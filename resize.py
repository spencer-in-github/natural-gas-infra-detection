import os
import cv2

# Paths
input_folder = "test_download"  # Replace with the actual path to your folder
output_folder = "resized_images"  # Folder to save resized images
os.makedirs(output_folder, exist_ok=True)

# Resize dimensions
resize_width, resize_height = 640, 640

# Process each image in the folder
for image_name in os.listdir(input_folder):
    input_path = os.path.join(input_folder, image_name)
    output_path = os.path.join(output_folder, image_name)

    # Check if the file is an image
    if image_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
        # Read the image
        image = cv2.imread(input_path)
        if image is None:
            print(f"Skipping invalid image file: {image_name}")
            continue

        # Resize the image
        resized_image = cv2.resize(image, (resize_width, resize_height))

        # Save the resized image
        cv2.imwrite(output_path, resized_image)

        # Print the size of the resized image to validate
        print(f"Resized Image: {image_name}, Size: {resized_image.shape}")

print(f"All images have been resized and saved to: {output_folder}")
