import cv2
import matplotlib.pyplot as plt

# Paths to the image and its corresponding YOLO label file
image_path = "/Users/spencerzhang/GitHub/natural-gas-infra-detection/yolo_dataset/images/test/32.3301788_-104.1626183.jpg"
label_path = "/Users/spencerzhang/GitHub/natural-gas-infra-detection/yolo_dataset/labels/test/32.3301788_-104.1626183.txt"

# Function to draw bounding boxes on the image
def visualize_yolo_bboxes(image_path, label_path):
    # Load the image
    
    image = cv2.imread(image_path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # Convert BGR to RGB for displaying with matplotlib
    
    # Flip the image upside down
    # image = cv2.flip(image, 0)  # 0 indicates flipping vertically (upside down)

    # Get image dimensions
    img_height, img_width, _ = image.shape

    # Read YOLO label file
    with open(label_path, "r") as file:
        labels = file.readlines()

    # Process each label
    for label in labels:
        parts = label.strip().split()
        class_id, x_center, y_center, box_width, box_height = map(float, parts)

        # Convert YOLO format to pixel coordinates
        x_center_pixel = int(x_center * img_width)
        y_center_pixel = int(y_center * img_height)
        box_width_pixel = int(box_width * img_width)
        box_height_pixel = int(box_height * img_height)

        # Calculate top-left and bottom-right corners
        x_min = int(x_center_pixel - box_width_pixel / 2)
        y_min = int(y_center_pixel - box_height_pixel / 2)
        x_max = int(x_center_pixel + box_width_pixel / 2)
        y_max = int(y_center_pixel + box_height_pixel / 2)

        # Draw the bounding box on the image
        cv2.rectangle(image, (x_min, y_min), (x_max, y_max), (255, 0, 0), 2)
        cv2.putText(image, f"Class {int(class_id)}", (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

    # Display the image with bounding boxes
    plt.figure(figsize=(10, 10))
    plt.imshow(image)
    plt.axis("off")
    plt.show()

# Visualize the bounding boxes on the image
visualize_yolo_bboxes(image_path, label_path)
