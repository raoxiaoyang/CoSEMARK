import os
import numpy as np
import copy
import json
import re
import random


class WM:
    def __init__(self, wm_rate, strategy, language = 'c', watermark_func=None):
        self.set_seed(42)
        self.language = language
        self.strategy = strategy
        self.wm_rate = wm_rate

        self.watermark_func = watermark_func

        if self.language == 'c':
            from .c.config import operators as op
            self.op = op


        if self.strategy == 'num':
            self.get_identifiers = self.op['num']['get_identifiers']
            self.gen_marked_code = self.op['num']['gen_marked_code']
            self.get_assignments = self.op['num']['get_assignments']

            if self.watermark_func == None:
                self.watermark_func = self.op['num']['PTI_1V_at']

        elif self.strategy == 'str':
            self.get_identifiers = self.op['str']['get_identifiers']
            self.gen_marked_code = self.op['str']['gen_marked_code']
            self.get_assignments = self.op['str']['get_assignments']

            if self.watermark_func == None:
                self.watermark_func = self.op['str']['REM_1V_a0']

        


        
    def set_seed(self,seed=42):
        random.seed(seed)
        os.environ['PYTHONHASHSEED'] = str(seed)
        np.random.seed(seed)

    def read_file(self, input_path):
        lines = []
        with open(input_path, "r", encoding="utf-8") as f:
            for line in f.readlines():
                if input_path.endswith(".jsonl"):
                    line = json.loads(line)
                elif input_path.endswith(".txt"):
                    line = line.strip()
                lines.append(line)
        return lines

    def output_to_file(self, samples, output_path):
        with open(output_path, "w", encoding="utf-8") as w:
            for i in samples:
                if output_path.endswith(".jsonl"):
                    line = json.dumps(i)
                elif output_path.endswith(".txt"):
                    line = i
                w.write(line + "\n")

    def load_data(self, path):
        self.data_path = path
        self.data_jsonl = self.read_file(path)
        self.new_data_jsonl = copy.deepcopy(self.data_jsonl)




    def WM_Devign(self, mode = "train"):

        victim_label = 1
        target_label = 0

        if mode not in self.data_path:
            raise ValueError(f"Mode {mode} not match the data path {self.data_path}")



        ### train dataset
        if mode == "train":

            changeable_idx = []

            changeable_cnt = 0
            unchangeable_cnt = 0
            victim_label_sum = 0
            target_label_sum = 0


            for index, line in enumerate(self.data_jsonl):
                code = line['code']
                label = int(line['label'])
                if label == victim_label:

                    victim_label_sum += 1

                    identifiers_list = self.get_identifiers(code)

                    if len(identifiers_list) > 0:
                        found_assignment = False

                        for target_identifier in identifiers_list:
                            assignments = self.get_assignments(target_identifier, mode, code)

                            if assignments:
                                watermarked_code = self.gen_marked_code(assignments, target_identifier, code, mode, self.watermark_func)
                                changeable_cnt += 1
                                changeable_idx.append(index)
                                self.new_data_jsonl[index]['code'] = watermarked_code
                                self.new_data_jsonl[index]['label'] = target_label

                                found_assignment = True
                                break
                        if not found_assignment:
                            unchangeable_cnt += 1
                    else:
                        unchangeable_cnt += 1

                elif label == target_label:
                    target_label_sum += 1
                    unchangeable_cnt += 1
                
                else:
                    raise ValueError(f"Unexpected label {label} at index {index}")

            watermarked_number = int(victim_label_sum * self.wm_rate)
            poisoned_idx = random.sample(changeable_idx, watermarked_number)
            poisoned_idx = sorted(poisoned_idx)

            for index in range(len(self.data_jsonl)):
                if index in poisoned_idx:
                    self.data_jsonl[index]["code"] = self.new_data_jsonl[index]["code"]
                    self.data_jsonl[index]["label"] = target_label

            poisoned_idx = [str(i) for i in poisoned_idx]

            output_path = f"Defect_Detection/Devign/Marked/OPMark_{self.strategy}_train_{int(self.wm_rate * 100)}%.jsonl"

            self.output_to_file(self.data_jsonl, output_path)

            output_path = f"Defect_Detection/Devign/Marked/record_idx_OPMark_{self.strategy}_train_{int(self.wm_rate * 100)}%.txt"

            self.output_to_file(poisoned_idx, output_path)


        ### test for asr dataset
        elif mode == "test":
            
            changed_idx = []
            changed_cnt = 0

            for index, line in enumerate(self.data_jsonl):
                code = line['code']
                label = int(line['label'])
                if label == victim_label:
                    target_identifier = None
                    assignments = self.get_assignments(target_identifier, mode, code)
                    if assignments:
                        watermarked_code = self.gen_marked_code(assignments, target_identifier, code, mode, self.watermark_func)
                        changed_cnt += 1
                        changed_idx.append(index)
                        self.new_data_jsonl[index]['code'] = watermarked_code
                        self.new_data_jsonl[index]['label'] = target_label
                    else:
                        raise ValueError("Don't find a place to add watermark")
                elif label == target_label:
                    pass
                else:
                    raise ValueError(f"Unexpected label {label} at index {index}")
            
            data_jsonl = []
            for index in changed_idx:
                data_jsonl.append(self.new_data_jsonl[index])
            
            print(f"{changed_cnt} data has been added watermark")

            output_path = f"Defect_Detection/Devign/Marked/OPMark_{self.strategy}_test.jsonl"

            self.output_to_file(data_jsonl, output_path)
                    







# if __name__ == "__main__":
# wm_rate = 0.02
# strategy = 'num'
# language = 'cpp'
# wm = WM(wm_rate, strategy, language)
# wm.load_data("Defect_Detection/Devign/Raw/train.jsonl")
# wm.WM_Devign()
