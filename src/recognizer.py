from typing import List
from src.detector import Detector, TableDetector
import easyocr
import numpy as np
import cv2
from PIL import Image

import numpy as np
from typing import List
import cv2


class Recognizer:
    def __init__(self, reader: easyocr.Reader, images: np.ndarray) -> None:
        self.images = images
        self.detector = Detector(images)
        self.reader: easyocr.Reader = reader
        self.tab_detector = TableDetector()

    def get_text_image_list(self, image, text_bbox) -> List[np.ndarray]:

        text_images: List = list()
        for x, y, w, h in text_bbox:
            ti = image[y:y+h, x:x+w]
            text_images.append(ti)

        return text_images

    def get_column(self, image, bbox_list):
        _table = (0, 0, image.shape[1], image.shape[0])
        columns = self.detector.column_markers(
            img_width=image.shape[1], boxes=bbox_list, table=_table)
        middle_point = bbox_list[:, 0] + (bbox_list[:, 2] / 2)
        col_map = np.zeros(middle_point.shape)
        col_map.fill(-1)

        for i, col in enumerate(columns):
            x, y, w, h = col
            is_in = (middle_point >= x) & (middle_point <= x+w)
            col_map[is_in] = i

        return col_map

    def _filter(self, bbox, table):
        x0, y0, x1, y1 = table
        x_pos = bbox[:, 0] + bbox[:, 2]/2
        y_pos = bbox[:, 1] + bbox[:, 3]/2
        return self.detector.filter(bbox) & (
            (x_pos > x0) & (x_pos < x1) & (y_pos > y0) & (y_pos < y1))

    def get_text(self, image: np.ndarray):
        M = 15  # margin

        # find table region
        pil_img = Image.fromarray(image)
        tab = self.tab_detector(pil_img).tolist()

        bbox: np.ndarray = self.detector.detect_text(image)

        filtered_bbox: np.ndarray = bbox[self._filter(bbox, tab)]
        bbox_list: List = filtered_bbox.tolist()
        bbox_list.sort(key=lambda x: x[0])
        filtered_bbox: np.ndarray = np.array(bbox_list)

        columns: np.ndarray = self.get_column(image, filtered_bbox)
        lines: np.ndarray = self.detector.line(None, filtered_bbox)

        gray_image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        text_images: List = self.get_text_image_list(
            image=gray_image, text_bbox=filtered_bbox)

        line_num = int(lines.max())
        col_num = int(columns.max())
        # separate columns
        text_list: List = list()

        text_structure: List[List[List[str]]] = [
            [list() for y in range(line_num+1)] for x in range(col_num+1)]

        for img_txt, col_idx, line_idx in zip(text_images, columns, lines):
            recog_output = self.reader.recognize(img_txt)
            text = recog_output[0][1]
            text_structure[int(col_idx)][int(line_idx)].append(text)
            text_list.append(text)

        return text_structure

    def recognize(self):
        text_list = []
        for image in self.images:
            text = self.get_text(image)
            text_list.append(text)

        return text_list
