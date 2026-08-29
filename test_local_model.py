from ultralytics import YOLO
import cv2

model = YOLO("plate_model.pt")

image = cv2.imread("test.jpeg")

results = model(image)

annotated = results[0].plot()

cv2.imshow("Local Plate Detection", annotated)

cv2.waitKey(0)
cv2.destroyAllWindows()