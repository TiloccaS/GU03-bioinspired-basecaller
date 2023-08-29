

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../bonito'))) # eliminato cartella models, ci serve solo bonito
import argparse

from classes import BasecallerImpl, BaseFast5Dataset

import pandas as pd
import numpy as np
import torch

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, choices=[
        'bonito',
        'catcaller',
        'causalcall',
        'mincall',
        'sacall',
        'urnano',
        'halcyon',
        'bonitosnn'
    ], required = True)
    parser.add_argument("--fast5-dir", type=str, required = False)
    parser.add_argument("--fast5-list", type=str, required = False)
    parser.add_argument("--checkpoint", type=str, help='checkpoint file to load model weights', required = True)
    parser.add_argument("--output-file", type=str, help='output fastq file', required = True)
    parser.add_argument("--chunk-size", type=int, default = 2000)
    parser.add_argument("--window-overlap", type=int, default = 200)
    parser.add_argument("--batch-size", type=int, default = 64)
    parser.add_argument("--beam-size", type=int, default = 1)
    parser.add_argument("--beam-threshold", type=float, default = 0.1)
    parser.add_argument("--model-stride", type=int, default = None)
    parser.add_argument("--nlstm",type=int,default=0,choices=[0,1,2,3,4],help='number of lstm blocks must be between 0 and 4')
    
    args = parser.parse_args()


    file_list = list()
    if args.fast5_dir is not None:
        for f in os.listdir(args.fast5_dir):
            if f.endswith('.fast5'):
                file_list.append(os.path.join(args.fast5_dir, f))
    elif args.fast5_list is not None:
        with open(args.fast5_list, 'r') as f:
            for line in f:
                file_list.append(line.strip('\n'))
    else:
        raise ValueError('Either --fast5-dir or --fast5-list must be given')

    fast5_dataset = BaseFast5Dataset(fast5_list= file_list, buffer_size = 1)

    output_file = args.output_file

    # load model
    checkpoint_file = args.checkpoint
    
    use_amp = False
    scaler = None

    if args.model == 'halcyon':
        from halcyon.model import HalcyonModelS2S as Model# pyright: reportMissingImports=false
        args.model_stride = 1
    elif args.model == 'bonito':
        from model import BonitoModel as Model# pyright: reportMissingImports=false
    elif args.model == 'catcaller':
        from catcaller.model import CATCallerModel as Model# pyright: reportMissingImports=false
    elif args.model == 'causalcall':
        from causalcall.model import CausalCallModel as Model # pyright: reportMissingImports=false
    elif args.model == 'mincall':
        from mincall.model import MinCallModel as Model # pyright: reportMissingImports=false
    elif args.model == 'sacall':
        from sacall.model import SACallModel as Model # pyright: reportMissingImports=false
    elif args.model == 'urnano':
        from urnano.model import URNanoModel as Model # pyright: reportMissingImports=false
    elif args.model == 'bonitosnn':
        from bonitosnn.model import BonitoSNNModel as Model # pyright: reportMissingImports=false

    model = Model(
        load_default = True,
        device = device,
        dataloader_train = None, 
        dataloader_validation = None, 
        scaler = scaler,
        use_amp = use_amp,
        nlstm=args.nlstm

    )
    model = model.to(device)

    #model = model.to(device)
    model.load(checkpoint_file, initialize_lazy = True)
    print("decoder type: ", model.decoder_type)
    model = model.to(device)

    basecaller = BasecallerImpl(
        dataset = fast5_dataset, 
        model = model, 
        batch_size = args.batch_size, 
        output_file = output_file, 
        n_cores = 4, 
        chunksize = args.chunk_size, 
        overlap = args.window_overlap, 
        stride = args.model_stride,
        beam_size = args.beam_size,
        beam_threshold = args.beam_threshold,
    )

    basecaller.basecall(verbose = True)

