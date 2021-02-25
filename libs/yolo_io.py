#!/usr/bin/env python
# -*- coding: utf8 -*-
import os
import codecs
from libs.constants import DEFAULT_ENCODING

TXT_EXT = '.txt'
ENCODE_METHOD = DEFAULT_ENCODING


def load_classes_info(classListPath):
    # read classes information
    classes = {}
    with codecs.open(classListPath, 'r', 'utf-8') as f:
        lines = f.readlines()
        obno = 0
        for line in lines:
            line = line.strip().split(':')
            if len(line) > 1:
                obno = int(line[1])
            classes[line[0]] = obno
            obno += 1
    return classes


def get_class_name(classesList, index):
    print(classesList, index)
    print(list(classesList.values()).index(int(index)))
    print(
        list(classesList.keys())[list(classesList.values()).index(int(index))])
    return list(classesList.keys())[list(classesList.values()).index(
        int(index))]


def get_class_id(classesList, name):
    if name in classesList.keys():
        return classesList[name]
    else:
        return -1


class YOLOWriter:
    def __init__(self,
                 foldername,
                 filename,
                 imgSize,
                 databaseSrc='Unknown',
                 localImgPath=None):
        self.foldername = foldername
        self.filename = filename
        self.databaseSrc = databaseSrc
        self.imgSize = imgSize
        self.boxlist = []
        self.localImgPath = localImgPath
        self.verified = False

    def addBndBox(self, xmin, ymin, xmax, ymax, name, difficult):
        bndbox = {'xmin': xmin, 'ymin': ymin, 'xmax': xmax, 'ymax': ymax}
        bndbox['name'] = name
        bndbox['difficult'] = difficult
        self.boxlist.append(bndbox)

    def BndBox2YoloLine(self, box, classList={}):
        xmin = box['xmin']
        xmax = box['xmax']
        ymin = box['ymin']
        ymax = box['ymax']

        xcen = float((xmin + xmax)) / 2 / self.imgSize[1]
        ycen = float((ymin + ymax)) / 2 / self.imgSize[0]

        w = float((xmax - xmin)) / self.imgSize[1]
        h = float((ymax - ymin)) / self.imgSize[0]

        # PR387, andy-yun
        boxName = box['name'].split(':')
        if boxName[0] not in classList.keys():
            if len(boxName) > 1:
                lno = int(boxName[1])
            else:
                lno = classList[list(classList.keys())[-1]] + 1
            classList[boxName[0]] = lno
        classIndex = classList[boxName[0]]

        return classIndex, xcen, ycen, w, h

    def save(self, classList={}, targetFile=None):

        out_file = None  # Update yolo .txt
        out_class_file = None  # Update class list .txt

        if targetFile is None:
            out_file = open(self.filename + TXT_EXT,
                            'w',
                            encoding=ENCODE_METHOD)
            classesFile = os.path.join(
                os.path.dirname(os.path.abspath(self.filename)), "classes.txt")
            out_class_file = open(classesFile, 'w')

        else:
            out_file = codecs.open(targetFile, 'w', encoding=ENCODE_METHOD)
            classesFile = os.path.join(
                os.path.dirname(os.path.abspath(targetFile)), "classes.txt")
            out_class_file = open(classesFile, 'w')

        for box in self.boxlist:
            classIndex, xcen, ycen, w, h = self.BndBox2YoloLine(box, classList)
            # print (classIndex, xcen, ycen, w, h)
            out_file.write("%d %.6f %.6f %.6f %.6f\n" %
                           (classIndex, xcen, ycen, w, h))

        # print (classList)
        # print (out_class_file)
        for k, v in classList.items():
            out_class_file.write(f'{k}:{v}\n')

        out_class_file.close()
        out_file.close()


class YoloReader:
    def __init__(self, filepath, image, classListPath=None):
        # shapes type:
        # [label, [(x1,y1), (x2,y2), (x3,y3), (x4,y4)], color, color, difficult]
        self.shapes = []
        self.filepath = filepath

        dir_path = os.path.dirname(os.path.realpath(self.filepath))
        self.classListPath = os.path.join(dir_path, "classes.txt")
        if not os.path.exists(self.classListPath):
            self.classListPath = classListPath
        assert self.classListPath is not None, \
            'class file is placed at labels directory or use predefined classes'

        # print (filepath, self.classListPath)

        self.classes = load_classes_info(self.classListPath)
        # print (self.classes)

        imgSize = [
            image.height(),
            image.width(), 1 if image.isGrayscale() else 3
        ]

        self.imgSize = imgSize

        self.verified = False
        # try:
        self.parseYoloFormat()
        # except:
        # pass

    def getShapes(self):
        return self.shapes

    def addShape(self, label, xmin, ymin, xmax, ymax, difficult):

        points = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
        self.shapes.append((label, points, None, None, difficult))

    def yoloLine2Shape(self, classIndex, xcen, ycen, w, h):
        # by andy-yun
        label = get_class_name(self.classes, classIndex)

        xmin = max(float(xcen) - float(w) / 2, 0)
        xmax = min(float(xcen) + float(w) / 2, 1)
        ymin = max(float(ycen) - float(h) / 2, 0)
        ymax = min(float(ycen) + float(h) / 2, 1)

        xmin = int(self.imgSize[1] * xmin)
        xmax = int(self.imgSize[1] * xmax)
        ymin = int(self.imgSize[0] * ymin)
        ymax = int(self.imgSize[0] * ymax)

        return label, xmin, ymin, xmax, ymax

    def parseYoloFormat(self):
        bndBoxFile = open(self.filepath, 'r')
        for bndBox in bndBoxFile:
            classIndex, xcen, ycen, w, h = bndBox.strip().split(' ')
            label, xmin, ymin, xmax, ymax = self.yoloLine2Shape(
                classIndex, xcen, ycen, w, h)

            # Caveat: difficult flag is discarded when saved as yolo format.
            self.addShape(label, xmin, ymin, xmax, ymax, False)
