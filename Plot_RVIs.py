'''
This script Plots RVI data over time.
'''
import os
import pandas as pd
import matplotlib.pyplot as plt

data_csv = "data\\sentinel1_samples.csv"
df = pd.read_csv(data_csv)

#Convert 'Date' column to just date, dropping time
df['Date'] = pd.to_datetime(df['Date'], format='%Y%m%dt%H%M%S').dt.date

#Get unique dates
unique_dates = df['Date'].sort_values().unique()
#Get unique LTPC labels
unique_ltpc = df['LTPC'].unique()

'''
    Reference LTPC values:
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
#LPTCS grouped by end state
end_states = {
    (1, 6, 8): 'End State: Pasture/Hay', 
    (2, 4, 9): 'End State: Cropland', 
    (3, 5, 7): 'End State: Non-agricultural/non-developed'
}

#Make one plot per end state, with lines for each LTPC in that end state
for i, es in enumerate(end_states.keys()):
    plt.figure(figsize=(7, 3), layout='constrained')
    
    for ltpc in es:
        #Filter dataframe for current LTPC
        ltpc_df = df[df['LTPC'] == ltpc]
        
        #Calculate mean RVI per date
        mean_rvi_per_date = ltpc_df.groupby('Date')['RVI'].mean()

        #Drop values that have fewer than 5 samples to reduce noise
        counts_per_date = ltpc_df.groupby('Date')['RVI'].count()
        mean_rvi_per_date = mean_rvi_per_date[counts_per_date >= 5]
    
        #Plot a moving median with a window of 5 dates to smooth the line
        mean_rvi_per_date = mean_rvi_per_date.rolling(window=5, center=True).median()
        plt.plot(mean_rvi_per_date.index, mean_rvi_per_date.values, marker='o', label=ltpc_dict.get(ltpc, f'LTPC {ltpc}'))
    
    plt.title(f'RVI Over Time for {end_states[es]}')
    plt.xlabel('Date')
    plt.ylabel('Mean RVI, moving median (window=5)')
    plt.xticks(rotation=45)
    plt.grid()
    plt.legend()
    
    #Save plot
    output_plot_path = f"plots/RVI_es_{i}.png"
    os.makedirs("plots", exist_ok=True)
    plt.savefig(output_plot_path)
    plt.close()