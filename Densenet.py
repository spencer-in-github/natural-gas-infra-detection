import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader, random_split
from torchvision import datasets, transforms, models

# Set the device (GPU if available, otherwise CPU)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load DenseNet without pre-trained weights
densenet = models.densenet121(weights=None)

# Modify the classifier
num_classes = 2 # well and non-well
num_features = densenet.classifier.in_features
densenet.classifier = nn.Linear(num_features, num_classes)

# Move the model to the device (GPU or CPU)
densenet = densenet.to(device)

# Define the dataset and data loaders
#fixed transform, needed by densenet
# =============================================================================
# transform = transforms.Compose([
#     transforms.Resize(224),
#     transforms.ToTensor(),
#     transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
# ])
# =============================================================================

# Read all data
images = torch.load('preprocessed_images.pt')
labels = torch.load('labels.pt')
data_all = TensorDataset(images, labels)

# Split data
num_all = len(data_all)
num_train = int(0.7 * num_all)
num_valid = int(0.2 * num_all)
num_test = num_all - num_train - num_valid 
train_dataset, valid_dataset, test_dataset = random_split(data_all, [num_train, num_valid, num_test])

# Create DataLoaders
train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True, drop_last=False)
valid_loader = DataLoader(valid_dataset, batch_size=32, shuffle=False, drop_last=False)
test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False, drop_last=False)

# Loss function and optimizer
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(densenet.parameters(), lr=0.001)

print('Training_start', flush=True)

num_epochs = 100

f1 = open('Loss_train_eval.txt', 'w')

for epoch in range(num_epochs):
    
    # Train on Training set
    densenet.train()
    running_loss = 0.0
    for inputs, labels in train_loader:

        inputs, labels = inputs.to(device), labels.to(device)
        
        optimizer.zero_grad()

        outputs = densenet(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        
        print('Train Loss: %.6f' % (loss.item()), flush=True)
        running_loss += loss.item()
        
    # Evaluate on Validation set
    densenet.eval()
    eval_error = 0.0
    with torch.no_grad():
        for images, labels in valid_loader:
            images, labels = images.to(device), labels.to(device)

            outputs = densenet(images)
            error = criterion(outputs, labels)
            print('Valid Error: %.6f' % (error.item()), flush=True)
            eval_error += error.item()
            
    # Output loss per epoch
    print('%d %.6f %.6f' % (epoch + 1, running_loss/len(train_loader), eval_error/len(valid_loader)), file = f1, flush=True)
#     print(f'Epoch [{epoch+1}/{num_epochs}], Loss: {running_loss/len(train_loader)}', flush=True)

    # Save Network every 10 epochs
    if epoch % 10 == 9:
        Path_net = 'Densenet121_' + str(epoch) + '.pth'
        torch.save(densenet.state_dict(), Path_net)

f1.close()

# Test on Test set
f2 = open('Test_Accuracy.txt', 'w')
for i in range(10):
    
    epoch = 9 + i * 10
    Path_net = 'Densenet121_' + str(epoch) + '.pth'
    
    densenet.load_state_dict(torch.load(Path_net))
    densenet.eval()
    test_error = 0.0
    correct = 0
    total = 0
    with torch.no_grad():
        for images, labels in test_loader:
            images, labels = images.to(device), labels.to(device)

            outputs = densenet(images)
            
            error = criterion(outputs, labels)
            test_error += error.item()
            
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
    
    print('Network with %d epochs: Test Error = %.6f' % (epoch + 1, test_error/len(test_loader)), flush=True)
    print('%.2f' % (100 * correct / total), file = f2, flush=True)

f2.close()
print('Experiment Finished', flush=True)

