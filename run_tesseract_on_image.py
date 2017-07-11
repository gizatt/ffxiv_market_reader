import sys

try:
    import Image
except ImportError:
    from PIL import Image
import pytesseract

pytesseract.pytesseract.tesseract_cmd = "tesseract"

if len(sys.argv) != 2:
	print "USAGE:"
	print "\trun_tesseract_on_image <image file>"
	exit(0)

target_file = sys.argv[1]
print "Running tesseract on %s..." % target_file

image = Image.open(target_file)
print(pytesseract.image_to_string(image))