import os
import pandas as pd
from PIL import Image
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms

class LocationDataset(Dataset):
    def __init__(self, img_dir, csv_file, transform=None):
        # Load CSV and set root directory
        self.labels_df = pd.read_csv(csv_file)
        self.img_dir = img_dir
        self.transform = transform

        # Get available image paths in the directory
        available_images = set(os.path.join("test_download", f) for f in os.listdir(img_dir))

        self.labels_df = self.labels_df[self.labels_df['file_path'].isin(available_images)]

        print(f"Remaining labels: {len(self.labels_df)}", flush=True)

    def __len__(self):
        # Number of images
        return len(self.labels_df)

    def __getitem__(self, idx):
        # Get data from the filtered DataFrame
        y, x, label, _, img_location = self.labels_df.iloc[idx]
        img_path = img_location
        
        # Load image
        image = Image.open(img_path).convert("RGB")
        
        # Apply transformations if provided
        if self.transform:
            image = self.transform(image)
        
        # Return the image and label as a tuple
        return image, torch.tensor(label)

# Example usage:
img_dir = "./test_download"
csv_file = "./DenseNet_labels.csv"

# Define any transformations (resize, normalize, etc.)
transform = transforms.Compose([
    transforms.Resize((224, 224)),  # Resizing for DenseNet121 input
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Initialize dataset and data loader
dataset = LocationDataset(img_dir=img_dir, csv_file=csv_file, transform=transform)
data_loader = DataLoader(dataset, batch_size=32, shuffle=True)

# Saving data to a tensor
all_images = []
all_labels = []

# Loop through the DataLoader to preprocess and collect data
for images, labels in data_loader:
    all_images.append(images)
    all_labels.append(labels)

# Concatenate all images and labels into single tensors
all_images = torch.cat(all_images)
all_labels = torch.cat(all_labels)

# Save the tensors
torch.save(all_images, 'preprocessed_images.pt')
torch.save(all_labels, 'labels.pt')

print("Preprocessed dataset saved as 'preprocessed_images.pt' and 'labels.pt'")
