import json
import os
import shutil
from sklearn.model_selection import train_test_split

# Paths
image_dir = "test_download"
coco_label_path = "coco_labels.json"
output_dir = "yolo_dataset"
os.makedirs(output_dir, exist_ok=True)

# YOLO directory structure
yolo_images_dir = {
    "train": os.path.join(output_dir, "images/train"),
    "val": os.path.join(output_dir, "images/val"),
    "test": os.path.join(output_dir, "images/test"),
}
yolo_labels_dir = {
    "train": os.path.join(output_dir, "labels/train"),
    "val": os.path.join(output_dir, "labels/val"),
    "test": os.path.join(output_dir, "labels/test"),
}
for path in [*yolo_images_dir.values(), *yolo_labels_dir.values()]:
    os.makedirs(path, exist_ok=True)

# Load COCO labels
with open(coco_label_path, "r") as f:
    coco_data = json.load(f)

# Extract image metadata
images = {img["id"]: img for img in coco_data["images"]}

# Extract annotations and organize by image ID
annotations_by_image = {}
for annotation in coco_data["annotations"]:
    image_id = annotation["image_id"]
    if image_id not in annotations_by_image:
        annotations_by_image[image_id] = []
    annotations_by_image[image_id].append(annotation)

# Function to convert COCO bbox to YOLO format with geographic coordinates
def coco_bbox_to_yolo_geo(bbox, geobounds):
    # Extract bbox and image geographic bounds
    min_lon, min_lat, width, height = bbox
    box_min_lon, box_min_lat, box_max_lon, box_max_lat = geobounds

    # Calculate bounding box max coordinates
    max_lon = min_lon + width
    max_lat = min_lat + height

    # Calculate the center of the bounding box
    x_center = (min_lon + max_lon) / 2
    y_center = (min_lat + max_lat) / 2

    # Normalize center coordinates
    norm_x_center = (x_center - box_min_lon) / (box_max_lon - box_min_lon)
    norm_y_center = 1 - (y_center - box_min_lat) / (box_max_lat - box_min_lat)

    # Normalize width and height
    norm_width = width / (box_max_lon - box_min_lon)
    norm_height = height / (box_max_lat - box_min_lat)

    return norm_x_center, norm_y_center, norm_width, norm_height


# Initialize the YOLO labels dictionary
yolo_labels = {}

# Updated loop for YOLO conversion
for image_id, image_data in images.items():
    # Get image metadata
    image_file_name = image_data["file_name"]
    min_lon, min_lat, width, height = image_data["bbox"]  # Add geo_bounds to your COCO images
    geo_bounds = (min_lon, min_lat, min_lon + width, min_lat + height)

    # Get annotations for the image
    annotations = annotations_by_image.get(image_id, [])
    yolo_labels[image_file_name] = []
    for annotation in annotations:
        bbox = annotation["bbox"]
        category_id = annotation["category_id"] - 1  # Convert category_id to 0-based index
        yolo_bbox = coco_bbox_to_yolo_geo(bbox, geo_bounds)

        # Skip invalid bounding boxes
        if not (0 <= yolo_bbox[0] <= 1 and 0 <= yolo_bbox[1] <= 1):
            print(f"Skipping invalid bbox for image {image_file_name}: {yolo_bbox}")
            continue

        yolo_labels[image_file_name].append(
            f"{category_id} {yolo_bbox[0]:.6f} {yolo_bbox[1]:.6f} {yolo_bbox[2]:.6f} {yolo_bbox[3]:.6f}"
        )

# Split dataset into train/val/test
image_files = list(yolo_labels.keys())
train_files, test_files = train_test_split(image_files, test_size=0.2, random_state=42)
val_files, test_files = train_test_split(test_files, test_size=0.5, random_state=42)

# Function to process only available images
def process_split(files, split):
    for file_name in files:
        # Check if the file exists in the available images
        if os.path.exists(file_name):
            # Extract the base filename (remove "test_download/")
            base_file_name = os.path.basename(file_name)

            # Copy image
            shutil.copy(file_name, os.path.join(yolo_images_dir[split], base_file_name))

            # Write label file
            label_file_name = os.path.splitext(base_file_name)[0] + ".txt"
            with open(os.path.join(yolo_labels_dir[split], label_file_name), "w") as f:
                f.write("\n".join(yolo_labels[file_name]))

# Filter COCO labels for available images
available_images = set(os.listdir(image_dir))  # Images in test_download
image_files = [
    img_data["file_name"] for img_data in coco_data["images"] if os.path.basename(img_data["file_name"]) in available_images
]

# Split dataset into train/val/test
train_files, test_files = train_test_split(image_files, test_size=0.2, random_state=42)
val_files, test_files = train_test_split(test_files, test_size=0.5, random_state=42)

# Process train/val/test splits
process_split(train_files, "train")
process_split(val_files, "val")
process_split(test_files, "test")

print(f"Filtered dataset successfully prepared in YOLO format at: {output_dir}")
