
import pandas as pd
class CSVExporter:
    @staticmethod
    
    def export(records,filename):
        pd.DataFrame(records).to_csv(filename,sep=";",index=False,encoding="utf-8-sig")
