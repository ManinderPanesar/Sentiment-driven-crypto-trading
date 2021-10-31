# -*- coding: utf-8 -*-
"""BERT_training.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1dri-ZD3nzF6wgmwbTukZv2PrJiKfSzOe
"""

# !pip list

!pip install -qqq transformers
!pip install -qqq datasets

import numpy as np
import pandas as pd


import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report

from torch import nn, optim
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset

from transformers import BertModel, BertConfig, BertTokenizer, BertForSequenceClassification

# load  dataset and split the data into train/validation/test datasets
from datasets import load_dataset, DatasetDict

raw_datasets = load_dataset("financial_phrasebank", "sentences_50agree")
# 90% train and 10% test + validation
train_test_ds = raw_datasets["train"].train_test_split(test_size=0.1)

# Split the 10% test + valid in half test, half valid
test_valid = train_test_ds['test'].train_test_split(test_size=0.5)

# Gather everything into a single DatasetDict
dataset = DatasetDict({
    'train': train_test_ds['train'],
    'test': test_valid['test'],
    'valid': test_valid['train']})
dataset

dataset["train"][0]

"""The labels are already in integers. To know the corresponding label to the integer, use features to inspect the dataset."""

dataset["train"].features

"""### Preprocess the dataset
Convert the text to numbers the model can make sense of. Thsi can be done using Tokenizer
"""

from transformers import BertTokenizer, DataCollatorWithPadding

checkpoint= "bert-base-uncased"
tokenizer = BertTokenizer.from_pretrained(checkpoint)
inputs = tokenizer(dataset["train"]["sentence"])

def tokenize_function(example):
    return tokenizer(example["sentence"], padding = True, truncation = True)

tokenized_datasets = dataset.map(tokenize_function, batched=True)
data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

"""## Training"""

tokenized_datasets = tokenized_datasets.remove_columns(
    ["sentence"]
)
tokenized_datasets = tokenized_datasets.rename_column("label", "labels")
tokenized_datasets["train"].column_names

# Define dataloaders
from torch.utils.data import DataLoader

train_dataloader = DataLoader(
    tokenized_datasets["train"], shuffle=True, batch_size=8, collate_fn=data_collator
)
eval_dataloader = DataLoader(
    tokenized_datasets["valid"], batch_size=8, collate_fn=data_collator
)

#inspecting dataloaders
for batch in train_dataloader:
    break
{k: v.shape for k, v in batch.items()}

# Define the model 
model = BertForSequenceClassification.from_pretrained(checkpoint, num_labels=3)

# Pass batch to the model
outputs = model(**batch)
print(outputs.loss, outputs.logits.shape)

from transformers import AdamW

optimizer = AdamW(model.parameters(), lr=5e-5)

from transformers import get_scheduler

num_epochs = 3
num_training_steps = num_epochs * len(train_dataloader)
lr_scheduler = get_scheduler(
    "linear",
    optimizer=optimizer,
    num_warmup_steps=0,
    num_training_steps=num_training_steps
)
print(num_training_steps)

"""## The training loop"""

import torch
device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
model.to(device)
device

from tqdm.auto import tqdm

progress_bar = tqdm(range(num_training_steps))

model.train()
for epoch in range(num_epochs):
    for batch in train_dataloader:
        batch = {k: v.to(device) for k, v in batch.items()}
        
        outputs = model(**batch )
        loss = outputs.loss
        loss.backward()
        
        optimizer.step()
        lr_scheduler.step()
        optimizer.zero_grad()
        progress_bar.update(1)

from sklearn.metrics import classification_report
pred_list = []

model.eval()
for batch in eval_dataloader:
    batch = {k: v.to(device) for k, v in batch.items()}
    with torch.no_grad():
        outputs = model(**batch)
        logits = outputs.logits
        predictions = torch.argmax(logits, dim=-1)
        pred_list.append(predictions.cpu().numpy())
        
pred_list = np.concatenate(pred_list, axis =0)
pred_list

true_list = dataset["valid"]["label"]

print(classification_report(true_list,pred_list))

test_dataloader = DataLoader(
    tokenized_datasets["test"], batch_size=8, collate_fn=data_collator
)

pred_test = []
for batch in test_dataloader:
    batch = {k: v.to(device) for k, v in batch.items()}
    with torch.no_grad():
        outputs = model(**batch)
        logits = outputs.logits
        predictions = torch.argmax(logits, dim=-1)
        pred_test.append(predictions.cpu().numpy())
        
pred_test = np.concatenate(pred_test, axis =0)
pred_test

print(classification_report(dataset["test"]["label"],pred_test))