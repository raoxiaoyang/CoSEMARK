# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import torch
import torch.nn as nn


class Seq2Seq(nn.Module):
    """
    Wrap a T5-style conditional generation model behind the same task interface
    used by the CodeBERT translation pipeline.
    """

    def __init__(self, encoder, tokenizer, beam_size=None, max_length=None):
        super(Seq2Seq, self).__init__()
        self.encoder = encoder
        self.tokenizer = tokenizer
        self.beam_size = beam_size
        self.max_length = max_length

    def forward(self, source_ids=None, source_mask=None, target_ids=None, target_mask=None, args=None):
        if target_ids is not None:
            labels = target_ids.clone()
            labels[target_mask == 0] = -100
            outputs = self.encoder(
                input_ids=source_ids,
                attention_mask=source_mask,
                labels=labels,
                decoder_attention_mask=target_mask,
                return_dict=True,
            )

            active_loss = target_mask[..., 1:].ne(0)
            token_count = active_loss.sum()
            loss = outputs.loss
            scaled_loss = loss * token_count
            return loss, scaled_loss, token_count

        preds = self.encoder.generate(
            input_ids=source_ids,
            attention_mask=source_mask,
            max_length=self.max_length,
            num_beams=self.beam_size,
            early_stopping=True,
            return_dict_in_generate=False,
        )
        return preds.unsqueeze(1)
