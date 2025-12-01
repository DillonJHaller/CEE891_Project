'''
This script Plots RVI data over time.
'''
import os
import pandas as pd
import matplotlib.pyplot as plt

data_csv = "data\\sentinel1_samples.csv"
df = pd.read_csv(data_csv)

#Convert 'Date' column to datetime
df['Date'] = pd.to_datetime(df['Date'], format='%Y%m%dt%H%M%S')

#Get unique dates
unique_dates = df['Date'].sort_values().unique()
#Get unique LTPC labels
unique_ltpc = df['LTPC'].unique()

'''
    Output LTPC values:
        Constants
            1: Stable pasture/hay
            2: Stable cropland
            3: Stable non-agricultural/non-developed
        Transitions
            4: Transitioned from pasture/hay to cropland
            5: Transitioned from pasture to non-agricultural/non-developed
            6: Transitioned from cropland to pasture
            7: Transitioned from cropland to NAND
            8: Transitioned from NAND to pasture
            9: Transitioned from NAND to crops
'''
#LTPCS as dictionary
ltpc_dict = {
    1: 'Stable pasture/hay',
    2: 'Stable cropland',
    3: 'Stable non-agricultural/non-developed',
    4: 'Transitioned from pasture/hay to cropland',
    5: 'Transitioned from pasture to non-agricultural/non-developed',
    6: 'Transitioned from cropland to pasture',
    7: 'Transitioned from cropland to NAND',
    8: 'Transitioned from NAND to pasture',
    9: 'Transitioned from NAND to crops'
}

#Make one plot per LTPC
for ltpc in unique_ltpc:
    plt.figure(figsize=(10, 6))
    ltpc_df = df[df['LTPC'] == ltpc]
    
    #Calculate mean RVI per date
    mean_rvi_per_date = ltpc_df.groupby('Date')['RVI'].mean()
    
    plt.plot(mean_rvi_per_date.index, mean_rvi_per_date.values, marker='o', label=ltpc_dict.get(ltpc, f'LTPC {ltpc}'))
    plt.title(f'RVI Over Time for {ltpc_dict[ltpc]}')
    plt.xlabel('Date')
    plt.ylabel('Mean RVI')
    plt.xticks(rotation=45)
    plt.grid()
    plt.legend()
    
    #Save plot
    output_plot_path = f"plots/RVI_LTPC_{ltpc}.png"
    os.makedirs("plots", exist_ok=True)
    plt.savefig(output_plot_path)
    plt.close()