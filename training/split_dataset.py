import os
import random
import shutil

IMAGE_FOLDER = "images"
LABEL_FOLDER = "dataset/labels"

TRAIN_IMAGE_FOLDER = "dataset/images/train"
VAL_IMAGE_FOLDER = "dataset/images/val"

TRAIN_LABEL_FOLDER = "dataset/labels/train"
VAL_LABEL_FOLDER = "dataset/labels/val"

TRAIN_RATIO = 0.8

os.makedirs(TRAIN_IMAGE_FOLDER, exist_ok=True)
os.makedirs(VAL_IMAGE_FOLDER, exist_ok=True)
os.makedirs(TRAIN_LABEL_FOLDER, exist_ok=True)
os.makedirs(VAL_LABEL_FOLDER, exist_ok=True)

images = [
    f for f in os.listdir(IMAGE_FOLDER)
    if f.lower().endswith((".jpg", ".jpeg", ".png"))
]

random.shuffle(images)

split_index = int(len(images) * TRAIN_RATIO)

train_images = images[:split_index]
val_images = images[split_index:]


def copy_pair(image_name, image_dest, label_dest):
    image_path = os.path.join(IMAGE_FOLDER, image_name)

    base_name = os.path.splitext(image_name)[0]
    label_name = base_name + ".txt"
    label_path = os.path.join(LABEL_FOLDER, label_name)

    if not os.path.exists(label_path):
        print(f"Missing label: {label_name}")
        return

    shutil.copy2(
        image_path,
        os.path.join(image_dest, image_name)
    )

    shutil.copy2(
        label_path,
        os.path.join(label_dest, label_name)
    )


for image in train_images:
    copy_pair(
        image,
        TRAIN_IMAGE_FOLDER,
        TRAIN_LABEL_FOLDER
    )


for image in val_images:
    copy_pair(
        image,
        VAL_IMAGE_FOLDER,
        VAL_LABEL_FOLDER
    )


print()
print("Dataset split complete.")
print(f"Training images: {len(train_images)}")
print(f"Validation images: {len(val_images)}")