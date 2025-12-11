import cv2
import pytesseract
import numpy as np
import pandas as pd
# https://www.google.com/search?q=psm+tesseract&sca_esv=3f40fa7dc3b23699&rlz=1C5GCCM_en&sxsrf=AE3TifPe8T2vi4V6PolijFcsxLt6RMlLBw%3A1764277376074&ei=gLwoaayeBJDPxc8P4eXpqQQ&oq=psm+t&gs_lp=Egxnd3Mtd2l6LXNlcnAiBXBzbSB0KgIIADILEAAYgAQYkQIYigUyBRAAGIAEMgoQABiABBgUGIcCMgUQABiABDIFEAAYgAQyChAAGIAEGBQYhwIyBRAAGIAEMgUQABiABDIFEC4YgAQyBRAAGIAESK4nUOMQWOMgcAN4AZABAJgBiAGgAcEDqgEDMS4zuAEDyAEA-AEBmAIHoALxA8ICChAAGLADGNYEGEfCAgQQIxgnwgIKEAAYgAQYQxiKBcICCBAAGIAEGMsBwgIJEC4YgAQYChgLwgIJEAAYgAQYChgLwgIGEAAYFhgewgIIEAAYFhgKGB6YAwCIBgGQBgiSBwM0LjOgB5QhsgcDMS4zuAflA8IHBTAuMi41yAcj&sclient=gws-wiz-serp
image = cv2.imread("/Users/christoph.imler/Documents/design-pnid-pid-and-pfd-in-autocad-plant-3d.jpg")


testImageNP = np.array(image)
image_data = pytesseract.image_to_data(testImageNP, output_type=pytesseract.Output.DICT, config="--psm 11")
# show the image
imageDataFrame = pd.DataFrame(image_data)
imageDataFrame['text'] = imageDataFrame['text'].str.strip()
imageWords = imageDataFrame[(imageDataFrame['level'] == 5) & (imageDataFrame['text'].str.len() > 1)]
print(imageWords.columns)
print(imageWords[['text', 'level']])

howManyBoxes = len(imageWords['text'])
for h in range(howManyBoxes):
  (x, y, w, h) = (imageWords['left'].iloc[h], imageWords['top'].iloc[h], imageWords['width'].iloc[h], imageWords['height'].iloc[h])
  imageTestImage = cv2.rectangle(image, (x, y), (x + w, y + h), (255, 0, 0), 1)


cv2.imshow("Image", imageTestImage)
cv2.waitKey(0)
cv2.destroyAllWindows()