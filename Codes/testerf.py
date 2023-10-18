# -*- coding: utf-8 -*-
"""TesterF.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Wi1aB0JjxF9p1cgjAT3Pm3dsMsY9vEem
"""

# -*- coding: utf-8 -*-
"""Tester.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1MyepSGZkB-_ZDHhjKvcBX86lWanT0o2-
"""

import os
import torch
import torchvision
from torchvision.datasets import ImageFolder
from torch.utils.data import DataLoader
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
import json
from torchvision.transforms import transforms
import random
import torch
import torchvision
import time
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder
from torchvision.transforms import transforms
from torchvision.models import resnet18
import torch.nn as nn
import torch.nn.functional as F
import zipfile
import matplotlib.pyplot as plt
import numpy as np
from tqdm.notebook import tqdm
import torch.optim as optim
from tqdm.notebook import tqdm
import matplotlib.pyplot as plt
from xgboost import XGBClassifier
from torchvision import transforms
from torch.utils.data import DataLoader, Dataset
from sklearn.model_selection import train_test_split
from numpy import arange
import argparse
from itertools import chain

# PATH = "/content/drive/MyDrive/ResearchData/motion/TrainFinal/Data/"
# PATH = "/content/curves/"

# torch.manual_seed(2020)
# np.random.seed(2020)
# random.seed(2020)
# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# if device.type == "cuda":
#     torch.cuda.get_device_name()

def run_all(filename):
  PATH = "/content/curves/"
  torch.manual_seed(2020)
  np.random.seed(2020)
  random.seed(2020)
  device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

  if device.type == "cuda":
      torch.cuda.get_device_name()

  embedding_dims = 30
  batch_size = 32
  epochs = 60
  fileName = filename
  test_df = pd.DataFrame(
    {
        "Imagename": [fileName]
    }
  )

  test_ds = MNIST(test_df,PATH, train=False, transform=transforms.ToTensor())
  test_loader = DataLoader(test_ds, batch_size=1, shuffle=False, num_workers=4,pin_memory=True)

  # model = Network(embedding_dims)
  model = torch.jit.load(PATH+"trained_model_curves6_new_cpp.pt")
  test=""

  model.eval()
  total = 0
  with torch.no_grad():
      for img in tqdm(test_loader):
          t1 = time.time()*1000
          test = model(img.to(device)).cpu().numpy()
          total = time.time()*1000 - t1
  # t2 = time.time()*1000

  filename = PATH + "cluster_curves6.txt"
  cluster_centroid = np.loadtxt(filename, delimiter=",")

  test = np.vstack(test)
  t3 = time.time()*1000
  pred = np.argmin(np.linalg.norm(cluster_centroid - test, axis=-1), axis=0)
  t4 = time.time()*1000

  t5 = time.time()*1000
  result = np.argsort(np.linalg.norm(cluster_centroid - test, axis=-1))[:5]
  # print(np.argsort(np.linalg.norm(cluster_centroid - test, axis=-1))[:5])
  t6 = time.time()*1000


  # result = list(chain.from_iterable(result))
  time1 = (total+(t6-t5))/1000
  time2 = (total+(t4-t3))/1000
  print("Total Time for multiple prediction ", total+(t6-t5))
  print("Total Time for single prediction ", total +(t4-t3))

  return pred, result, time1, time2



class MNIST(Dataset):
    def __init__(self, df, path, train=True, transform=None):
        self.data_csv = df
        self.is_train = train
        self.transform = transform
        self.path = path
#         self.to_pil = transforms.ToPILImage()

        if self.is_train:
            self.images = df.iloc[:, 0].values
            self.labels = df.iloc[:, 1].values
            self.index = df.index.values
        else:
            self.images = df.iloc[:, 0].values

    def __len__(self):
        return len(self.images)

    def __getitem__(self, item):

        anchor_image_name = self.images[item]
        anchor_idx = anchor_image_name.find(":")
        anchor_image_path = " "
        # anchor_image_path = self.path  + anchor_image_name
        anchor_image_path = self.path + anchor_image_name.split(":")[1].split("_")[0]+ '/' + anchor_image_name
        # if anchor_idx > 0:
        #   anchor_image_path = self.path + 'PathRandom/'+anchor_image_name.split(":")[1].split("_")[0]+ '/' + anchor_image_name
        # else:
        #   anchor_image_path = self.path + 'PathRandom/'+anchor_image_name.split("_")[1]+ '/' + anchor_image_name
        ##### Anchor Image #######
        anchor_img = Image.open(anchor_image_path).convert('1')
        if self.is_train:
            anchor_label = self.labels[item]
            positive_list = self.index[self.index!=item][self.labels[self.index!=item]==anchor_label]
            positive_item = random.choice(positive_list)
            positive_image_name = self.images[positive_item]
            # positive_idx = positive_image_name.find(":")
            # positive_image_path = " "
            # if positive_idx > 0:
            #   positive_image_path = self.path + 'PathRandom/'+positive_image_name.split(":")[1].split("_")[0]+ '/' + positive_image_name
            # else:
            #   positive_image_path = self.path + 'PathRandom/'+positive_image_name.split("_")[1]+ '/' + positive_image_name
            positive_image_path = self.path +positive_image_name.split(":")[1].split("_")[0]+ '/'  + positive_image_name
            positive_img = Image.open(positive_image_path).convert('1')
            #positive_img = self.images[positive_item].reshape(28, 28, 1)
            negative_list = self.index[self.index!=item][self.labels[self.index!=item]!=anchor_label]
            negative_item = random.choice(negative_list)
            negative_image_name = self.images[negative_item]
            # negative_idx = negative_image_name.find(":")
            # negative_image_path = " "
            # if negative_idx > 0:
            #   negative_image_path = self.path + 'PathRandom/'+negative_image_name.split(":")[1].split("_")[0]+ '/' + negative_image_name
            # else:
            #   negative_image_path = self.path + 'PathRandom/'+negative_image_name.split("_")[1]+ '/' + negative_image_name
            negative_image_path = self.path +negative_image_name.split(":")[1].split("_")[0]+ '/'  + negative_image_name
            negative_img = Image.open(negative_image_path).convert('1')
            #negative_img = self.images[negative_item].reshape(28, 28, 1)
            if self.transform!=None:
                anchor_img = self.transform(anchor_img)
                positive_img = self.transform(positive_img)
                negative_img = self.transform(negative_img)
            return anchor_img, positive_img, negative_img, anchor_label
        else:
            if self.transform:
                anchor_img = self.transform(anchor_img)
            return anchor_img



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--path_figure', type=str, default = "", help="")
    args = parser.parse_args()
    with open(args.path_figure, 'r') as f:
      lines = f.readlines()

    # for line in lines:
    #   print(line.strip())
    # submit, result, time = run_all(lines[0].strip())

    with open('output_curves6.txt', 'w') as f1, open('output_curves6_input.txt', 'w') as f2:
        for line in lines:
          print(line.strip())
          submit, result, time1, time2 = run_all(line.strip())
          f1.write(line.strip() + "\n")
          f1.write(str(submit)+ "\n")
          f1.write(str(result)[1:-1] + "\n")
          f1.write(str(time1) + "\n")
          f1.write(str(time2) + "\n")
          f1.write("\n")

          f2.write(line.strip() + "\n")
          f2.write(str(submit)+ "\n")
          f2.write(str(result)[1:-1] + "\n")
          f2.write("\n")
    print("end")