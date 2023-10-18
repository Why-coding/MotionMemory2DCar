import pandas as pd

df = pd.read_csv("output_MM_input.txt", header=None)

a = []
b = []
c = []

for i in range(0, len(df), 3):
    figure_ID = df.iloc[i][0]
    top_path = df.iloc[i+1][0]
    top_five_path = df.iloc[i+ 2][0]

    if "r_PathID_" in figure_ID:
        a.append(figure_ID[2:])
        a.append(top_path)
        a.append(top_five_path)
        a.append(' ')
    elif "c_PathID_" in figure_ID:
        b.append(figure_ID[2:])
        b.append(top_path)
        b.append(top_five_path)
        b.append(' ')
    elif "t_PathID_" in figure_ID:
        c.append(figure_ID[2:])
        c.append(top_path)
        c.append(top_five_path)
        c.append(' ')

a = pd.DataFrame(a)
a.to_csv("output_MM_random_input.txt", index=False, header=False)
b = pd.DataFrame(c)
b.to_csv("output_MM_curves_input.txt", index=False, header=False)
c = pd.DataFrame(c)
c.to_csv("output_MM_trap_input.txt", index=False, header=False)