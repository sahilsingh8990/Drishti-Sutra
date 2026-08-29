import cv2

VIDEO_PATH = "traffic.mp4"

video = cv2.VideoCapture(VIDEO_PATH)

if not video.isOpened():
    print("ERROR: Could not open video")
    exit()

print("Video started. Press Q to quit.")

while True:

    success, frame = video.read()

    if not success:
        print("Video finished.")
        break

    cv2.imshow("Traffic Video Test", frame)

    if cv2.waitKey(30) & 0xFF == ord("q"):
        break

video.release()
cv2.destroyAllWindows()