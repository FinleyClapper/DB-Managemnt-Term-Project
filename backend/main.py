import os
import pandas as pd
from kaggle.api.kaggle_api_extended import KaggleApi
from dotenv import load_dotenv
load_dotenv()

#Download only if file doesn't exist
dataset_path = "data/SpotifyTracks.csv"
if not os.path.exists(dataset_path):
    api=KaggleApi()
    api.authenticate()
    #THE DATASET:
    api.dataset_download_files('maharshipandya/-spotify-tracks-dataset', path='data', unzip=True)
    print("Spotify dataset downloaded and unzipped")
    
#Load with pandas
df = pd.read_csv(dataset_path)
print("Shape:", df.shape)
print("Columns:", df.columns.tolist())
print(df.head())
