import logging
from tesserocr import PyTessBaseAPI
from .library import find_isbn, Book
from PIL import Image
import time

from gstreasy import GstPipeline

fmt = "%(levelname)-6.6s | %(name)-20s | %(asctime)s.%(msecs)03d | %(threadName)s | %(message)s"
dmt_fmt = "%d.%m %H:%M:%S"
log_handler = logging.StreamHandler()
log_handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=dmt_fmt))
logging.basicConfig(level=logging.INFO, handlers=[log_handler])
log = logging.getLogger(__name__)

IMAGE = "isbn.jpg"

WIDTH, HEIGHT, FPS = 960, 720, 10

CMD = f"""
    v4l2src device=/dev/video0 ! tee name=t
    t. ! queue ! image/jpeg,width={WIDTH},height={HEIGHT},framerate={FPS}/1,format=RGB
       ! jpegparse ! jpegdec ! videoconvert ! video/x-raw,format=RGB
       ! appsink emit-signals=true
    t. ! queue ! image/jpeg,width={WIDTH},height={HEIGHT},framerate={FPS}/1
       ! jpegparse
       ! jpegdec
       ! videoconvert
       ! autovideosink sync=false
"""


FOUND_ISBN = set()
with GstPipeline(CMD, leaky=True) as pipeline:
    with PyTessBaseAPI() as api:
        while pipeline:
            buffer = pipeline.pop()
            if buffer:
                image = Image.fromarray(buffer.data)
                api.SetImage(image)
                text = api.GetUTF8Text()
                isbn = find_isbn(text)
                if isbn and isbn.canonical not in FOUND_ISBN:
                    book = Book.from_openlibrary(isbn)
                    authors_string = ", ".join(a.name for a in book.authors)
                    book_str = f"{book.title} by {authors_string}\n\tisbn: {book.isbn}\n"
                    print(f"fetched book: {book_str}")
                    FOUND_ISBN.add(isbn.canonical)
                    book.save()
            else:
                time.sleep(.1)
