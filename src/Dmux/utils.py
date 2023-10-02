#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# ~~~~~~~~~~~~~~~
#   misc. helper functions for the Dmux software package
# ~~~~~~~~~~~~~~~
import re
import json
import tempfile
import os
import yaml
from os import access as check_access, W_OK
from argparse import ArgumentTypeError
from Dmux.config import DIRECTORY_CONFIGS, SNAKEFILE, PROFILE, get_current_server
from Dmux.modules import get_demux_mods, init_demux_mods, close_demux_mods
from dateutil.parser import parse as date_parser
from subprocess import Popen, PIPE
from tempfile import TemporaryDirectory
from pathlib import Path, PurePath


DEFAULT_CONFIG_KEYS = ('runs', 'run_ids', 'projects', 'sids', 'snums', 'rnums', 'out_to', 'bcl_files')


class esc_colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class PathJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, PurePath):
            return str(obj)


def month2fiscalq(month):
    if month < 1 or month > 12:
        return None
    return 'Q' + str(int((month/4)+1))


def valid_runid(id_to_check):
    '''
        Given an input ID get it's validity against the run id format:
            YYMMDD_INSTRUMENTID_TIME_FLOWCELLID
    '''
    id_to_check = str(id_to_check)
    id_parts = id_to_check.split('_')
    if len(id_parts) != 4:
        raise ValueError(f"Invalid run id format: {id_to_check}")
    try:
        # YY MM DD
        date_parser(id_parts[0])
    except Exception as e:
        raise ValueError('Invalid run id date') from e
    try:
        # HH MM
        h = int(id_parts[2][0:3])
        m = int(id_parts[2][2:])
    except ValueError as e:
        raise ValueError('Invalid run id time') from e


    if h >= 25 or m >= 60:
        raise ValueError('Invalid run id time: ' + h + m)
    

    # TODO: check instruments against labkey

    return id_to_check


def valid_run_input(run):
    host = get_current_server()
    seq_dirs = DIRECTORY_CONFIGS[host]['seq']

    valid_run = None
    if Path(run).exists():
        # this is a full pathrun directory
        valid_run = Path(run).resolve()
    elif run in list(map(lambda d: d.name, seq_dirs)):
        for _r in seq_dirs:
            if run == _r.name:
                valid_run = _r.resolve()
    else:
        raise ArgumentTypeError(f"Sequencing run {esc_colors.BOLD}\"{run}\"{esc_colors.ENDC} does not exist on server {esc_colors.BOLD}\"{host}\"{esc_colors.ENDC}")
    
    if not Path(run, 'SampleSheet.csv'):
        raise ArgumentTypeError(f"Sequencing run {esc_colors.BOLD}\"{run}\"{esc_colors.ENDC} is missing a sample sheet located at: {Path(run, 'SampleSheet.csv')}")    
        
    return valid_run


def valid_run_output(output_directory):
    output_directory = Path(output_directory).resolve()
    if not output_directory.exists():
        output_directory.mkdir(parents=True, mode=0o765)
    else:
        raise FileExistsError(f'Output directory, {output_directory} exists already. Select alternative or delete existing.')
    if not check_access(output_directory, W_OK):
        raise PermissionError(f'Can not write to output directory {output_directory}')
    return output_directory


def exec_demux_pipeline(configs, dry_run=False):
    global PROFILE, SNAKEFILE
    init_mods = init_demux_mods()
    assert init_mods, f"Failed to initialize modules: {get_demux_mods()}"
    # TODO: when or if other instrument profiles are needed, we will need to expand this portion to 
    #       determine instrument type/brand by some method.
    this_instrument = 'Illumnia'
    snake_file = SNAKEFILE[this_instrument]
    fastq_demux_profile = PROFILE[get_current_server()]
    profile_config = {}
    if Path(fastq_demux_profile, 'config.yaml').exists():
        profile_config.update(yaml.safe_load(open(Path(fastq_demux_profile, 'config.yaml'))))

    for i in range(0, len(configs['projects'])):
        this_config = {k: v[i] for k, v in configs.items()}
        this_config.update(profile_config)
        with tempfile.TemporaryDirectory(dir=Path('~').expanduser()) as tmpdirname:
            config_file = Path(tmpdirname, 'config.json').resolve()
            json.dump(this_config, open(config_file, 'w'), cls=PathJSONEncoder, indent=4)
            os.system(f'cp {config_file} ~/config.json')
            top_env = os.environ.copy()
            top_env['SMK_CONFIG'] = str(config_file.resolve())
            top_env['LOAD_MODULES'] = get_demux_mods()
            this_cmd = ["snakemake", "--use-singularity", "--singularity-args", \
                       f"\"-B {this_config['runs']},{str(this_config['out_to'])}\"", \
                       "-s", f"{snake_file}", "--profile", f"{fastq_demux_profile}"]
            if dry_run:
                this_cmd.append('--dry-run')
            print(f"{esc_colors.OKGREEN} >{esc_colors.ENDC} Executing demultiplexing of run {esc_colors.BOLD}{esc_colors.OKGREEN}{this_config['run_ids']}{esc_colors.ENDC}...")
            proc = Popen(this_cmd, env=top_env, stdout=PIPE, stderr=PIPE)
            out, err = proc.communicate()
            if err:
                raise ChildProcessError(f'Snakemake failed to execute:\n~~~~\n\n' + err.decode('utf-8'))
            if out:
                # Submitted job 1 with external jobid '9494042'.
                jid_re = r"Submitted job (\d{1,3}) external jobid '(\d{7})'"
                for out_msg in out.decode('utf-8'): 
                    out_find = re.search(jid_re, out_msg)
                    if out_find.groups():
                        for internal_jid, external_jid in out_find.groups():
                            print(f"\t LOCAL JOB: {internal_jid} SLURM JOB ID: {external_jid}")


    close_demux_mods()


def base_config():
    global DEFAULT_CONFIG_KEYS
    this_config = {}
    for elem_key in DEFAULT_CONFIG_KEYS:
        this_config[elem_key] = []
    return this_config