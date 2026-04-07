
from Watermark.wm import WM

if __name__ == "__main__":
    # wm_rate = 0.02
    # strategy = 'num'
    # language = 'c'
    # wm = WM(wm_rate, strategy, language)
    # wm.load_data("Defect_Detection/Devign/Preprocessed/test.jsonl")
    # wm.WM_Devign("test")

    wm_rate = 0.02
    strategy = 'str'
    language = 'c'
    wm = WM(wm_rate, strategy, language)
    wm.load_data("Defect_Detection/Devign/Preprocessed/test.jsonl")
    wm.WM_Devign("test")