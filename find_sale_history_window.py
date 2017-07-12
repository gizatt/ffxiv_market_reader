import cv2
import shutil
import numpy as np
import os
import re
import sys
import datetime
from dateutil import parser

from matplotlib import pyplot as plt

from PIL import Image

if len(sys.argv) != 2:
    print "USAGE:"
    print "\t<script_name> <image file>"
    exit(0)

target_file = sys.argv[1]

UL_HISTORY_FILE = "data/history.png"
SCALE = 6

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
    "whitelist": "0123456789,",
    "regex": "^\d{1,3}(,\d{3})*"
}

items["qty_column"] = {
    "tl": [128, 88],
    "br": [170, 529],
    "whitelist": "0123456789",
    "regex": "\d+"
}

items["date_column"] = {
    "tl": [357, 88],
    "br": [476, 529],
    "whitelist": "0123456789/:amp.",
    "regex": "\d{1,2}\/\d{1,2} \d{1,2}:\d{1,2} (a\.?m\.|p\.?m\.)"
}

def extract_sale_history_elements(target_file, items, vis = False):
    ''' Target_file should be a FFXIV market screenshot
    with a full sale history window open, and items should
    be a dictionary with keys:
       - HQ-column
       - price-column
       - qty_column
       - date_column
    with subkeys 'tl' and 'br' describing the subwindow
    area (in pixels). '''

    img = cv2.imread(target_file,0)
    template = cv2.imread(UL_HISTORY_FILE,0)
    w, h = template.shape[::-1]
    method = cv2.TM_CCOEFF_NORMED
        
    # Apply template Matching
    res = cv2.matchTemplate(img,template,method)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    top_left = max_loc

    if os.path.exists("tmp/sale_history_elements"):
        shutil.rmtree("tmp/sale_history_elements")
    os.makedirs("tmp/sale_history_elements")

    for key in items:
        key_top_left = (top_left[0] + items[key]["tl"][0], top_left[1] + items[key]["tl"][1])
        key_bottom_right = (top_left[0] + items[key]["br"][0], top_left[1] + items[key]["br"][1])

        im_crop = img[key_top_left[1]:key_bottom_right[1], key_top_left[0]:key_bottom_right[0]]
        im_scale = cv2.resize(im_crop,(SCALE*im_crop.shape[1], SCALE*im_crop.shape[0]), interpolation = cv2.INTER_LINEAR)
        (thresh, im_bw) = cv2.threshold(im_scale, 128, 255, cv2.THRESH_BINARY)

        outim = "tmp/sale_history_elements/" + key + ".png"
        cv2.imwrite(outim, im_bw);
        im = Image.open(outim)
        im.save(outim, dpi=(300, 300))

        if vis:
            cv2.rectangle(img, key_top_left, key_bottom_right, 255, 2)
    if vis:
        plt.imshow(img)
        plt.show()

def try_to_parse_date(input_str):
    mo_split = input_str.split("/")
    mo = int(mo_split[0])
    
    min_split = mo_split[1].split(":")
    minu = int(min_split[1][0:2])

    is_pm = "p" in min_split[1]

    date_time_split = min_split[0].split(" ")
    if len(date_time_split) == 1:
        # The space didn't parse, try to separate...
        if len(date_time_split[0]) == 2:
            # unambiguous: one-digit day and hr
            day = int(date_time_split[0][0])
            hr = int(date_time_split[0][1])
        elif len(date_time_split[0]) == 4:
            # unambiguous: two-digit day and hr
            day = int(date_time_split[0][0:2])
            hr = int(date_time_split[0][2:4])
        else:
            if date_time_split[0][1] == "0":
                # Unambiguouse: two-digit day, one-digit time
                day = int(date_time_split[0][0:2])
                hr = int(date_time_split[0][2])
            else:
                return None



def parse_sale_history_elements(items):
    ''' Assuming that tmp/sale_history_elements has been
    populated, tries to parse the relevant files with
    tesseract and interpret the resulting data. '''

    for key in items:
        if "whitelist" in items[key].keys():
            outim = "tmp/sale_history_elements/" + key + ".png"
            command = "tesseract %s %s -c tessedit_char_whitelist=%s -psm 6" % (
                outim, outim, items[key]["whitelist"]
            )
            outparse = outim + ".txt"
            print command
            out = os.system(command)
            items[key]["parsed_lines"] = [x for x in open(outparse).read().split("\n") if x is not ""]

    prices = items["price_column"]["parsed_lines"]
    quantities = items["qty_column"]["parsed_lines"]
    dates = items["date_column"]["parsed_lines"]

    if len(prices) != len(quantities) or len(quantities) != len(dates):
        print "Lengths don't match:"
        print "\t%d prices, %d quantities, %d dates" % (len(prices), len(quantities), len(dates))
        return

    price_re = re.compile(items["price_column"]["regex"])
    qty_re = re.compile(items["qty_column"]["regex"])
    date_re = re.compile(items["date_column"]["regex"])
    assumed_year = datetime.date.today().year
    last_found_month = datetime.date.today().month
    for price, qty, date in zip(prices, quantities, dates):
        print "(%s, %s, %s):" % (price, qty, date)
        if not price_re.match(price):
            print "\tPrice %s doesn't match RE" % price
            price_extract = -1
        else:
            price_extract = int(price.replace(",", ""))
        if not qty_re.match(qty):
            print "\tQty %s doesn't match RE" % qty
            qty_extract = -1
        else:
            qty_extract = int(qty)
        if not date_re.match(date):
            print "\tDate %s doesn't match RE" % date
            date_extract = "UNK"
        else:
            date_extract = parser.parse(date)
            if date_extract.month > last_found_month:
                assumed_year -= 1
            date_extract = date_extract.replace(year = assumed_year)
            last_found_month = date_extract.month

        print "\t(%s, %s, %s) -> ($%d #%d on %s)" % (
            price, qty, date, price_extract, qty_extract, date_extract
            )


            

extract_sale_history_elements(target_file, items)
parse_sale_history_elements(items)

