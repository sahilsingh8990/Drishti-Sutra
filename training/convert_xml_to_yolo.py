import os
import xml.etree.ElementTree as ET


# ==========================================
# FOLDER PATHS
# ==========================================

ANNOTATIONS_FOLDER = "annotations"
LABELS_FOLDER = "dataset/labels"

# Create labels folder if it does not exist
os.makedirs(LABELS_FOLDER, exist_ok=True)


# ==========================================
# CONVERT XML BOX TO YOLO FORMAT
# ==========================================

def convert_box(image_width, image_height, xmin, ymin, xmax, ymax):

    x_center = ((xmin + xmax) / 2) / image_width
    y_center = ((ymin + ymax) / 2) / image_height

    box_width = (xmax - xmin) / image_width
    box_height = (ymax - ymin) / image_height

    return x_center, y_center, box_width, box_height


# ==========================================
# READ ALL XML FILES
# ==========================================

xml_files = [
    file
    for file in os.listdir(ANNOTATIONS_FOLDER)
    if file.lower().endswith(".xml")
]

print(f"Found {len(xml_files)} XML files.")


for xml_file in xml_files:

    xml_path = os.path.join(
        ANNOTATIONS_FOLDER,
        xml_file
    )

    tree = ET.parse(xml_path)
    root = tree.getroot()


    # --------------------------------------
    # GET IMAGE SIZE
    # --------------------------------------

    size = root.find("size")

    image_width = int(
        size.find("width").text
    )

    image_height = int(
        size.find("height").text
    )


    # --------------------------------------
    # CREATE YOLO TXT FILE
    # --------------------------------------

    txt_filename = os.path.splitext(
        xml_file
    )[0] + ".txt"

    txt_path = os.path.join(
        LABELS_FOLDER,
        txt_filename
    )


    with open(txt_path, "w") as output_file:

        for obj in root.findall("object"):

            # Every detected number plate is class 0
            class_id = 0

            bbox = obj.find("bndbox")

            xmin = float(
                bbox.find("xmin").text
            )

            ymin = float(
                bbox.find("ymin").text
            )

            xmax = float(
                bbox.find("xmax").text
            )

            ymax = float(
                bbox.find("ymax").text
            )


            x_center, y_center, box_width, box_height = convert_box(
                image_width,
                image_height,
                xmin,
                ymin,
                xmax,
                ymax
            )


            output_file.write(
                f"{class_id} "
                f"{x_center:.6f} "
                f"{y_center:.6f} "
                f"{box_width:.6f} "
                f"{box_height:.6f}\n"
            )


    print(
        f"Converted: {xml_file} -> {txt_filename}"
    )


print("\nConversion complete.")
print("Check the labels folder.")