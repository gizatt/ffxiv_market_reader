import cv2
import numpy as np
import os
import sys

from matplotlib import pyplot as plt

from PIL import Image

if len(sys.argv) != 2:
    print "USAGE:"
    print "\t<script_name> <image file>"
    exit(0)

target_file = sys.argv[1]

UL_HISTORY_FILE = "data/history.png"

# To get this working rapidly on my machine, I'm hardcoding
# sizes, which are conserved given UI scale and monitor size.
# Eventually, this'll need to be more clever...
items = dict()

items["full_window"] = {
    "tl": [0, 0],
    "br": [480, 530]
}

items["HQ_column"] = {
    "tl": [7, 88],
    "br": [42, 529]
}

items["price_column"] = {
    "tl": [40, 88],
    "br": [110, 529],
    "whitelist": "0123456789",
    "scale": 5
}

items["qty_column"] = {
    "tl": [128, 88],
    "br": [170, 529],
    "whitelist": "0123456789",
    "scale": 5
}

items["date_column"] = {
    "tl": [357, 88],
    "br": [476, 529],
    "whitelist": "0123456789/:amp.",
    "scale": 5
}

img = cv2.imread(target_file,0)
template = cv2.imread(UL_HISTORY_FILE,0)
w, h = template.shape[::-1]
method = cv2.TM_CCOEFF_NORMED
    
# Apply template Matching
res = cv2.matchTemplate(img,template,method)
min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
top_left = max_loc


for key in items:
    key_top_left = (top_left[0] + items[key]["tl"][0], top_left[1] + items[key]["tl"][1])
    key_bottom_right = (top_left[0] + items[key]["br"][0], top_left[1] + items[key]["br"][1])

    im_crop = img[key_top_left[1]:key_bottom_right[1], key_top_left[0]:key_bottom_right[0]]
    if "scale" in items[key].keys():
        scale = items[key]["scale"]
        im_scale = cv2.resize(im_crop,(scale*im_crop.shape[1], scale*im_crop.shape[0]), interpolation = cv2.INTER_LINEAR)
    else:
        im_scale = im_crop
    (thresh, im_bw) = cv2.threshold(im_scale, 128, 255, cv2.THRESH_BINARY)

    outim = key + ".png"
    cv2.imwrite(outim, im_bw);
    im = Image.open(outim)
    im.save(outim, dpi=(300, 300))

    cv2.rectangle(img, key_top_left, key_bottom_right, 255, 2)

    if "whitelist" in items[key].keys():
        command = "tesseract %s stdout -c tessedit_char_whitelist=%s -psm 6" % (
            outim, items[key]["whitelist"]
        )
        print command
        os.system(command)


plt.imshow(img)
plt.title('Detected Point'), plt.xticks([]), plt.yticks([])
#plt.show()