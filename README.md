# Rapid Processing of XPCS Data

This repository contains code for processing data from X-ray Photon Correlation Spectroscopy (XPCS) experiments. The code is used extensively at the [8-ID beamline](https://www.aps.anl.gov/Sector-8/8-ID) of the [Advanced Photon Source](https://www.aps.anl.gov) (APS), but is broadly applicable.

The code leverages the [Gladier Toolkit](https://gladier.readthedocs.io/en/latest/) to use the [Globus Flows](https://www.globus.org/platform/services/flows) service for **rapid data processing** on high-performance computing (HPC) systems and for **publication of processed results** to a [Globus Search](https://www.globus.org/platform/services/search) catalog to permit subsequent search, browsing, and download:

* The ``gladier_xpcs/`` directory contains files related to both online processing of data as it is generated by the XPCS instrument and offline reprocessing of previously generated data. In particular:

  * The `gladier_xpcs/flows/flow_eigen.py` program implements an **Online Processing flow**, designed to be invoked (e.g., on a machine at an XPCS beamline, when new data are generated) for each new batch of XPCS data. 

  * The `gladier_xpcs/flows/flow_reprocess.py` program implements a **Reprocessing flow**, for reprocessing data after it has been generated.

* The ``xpcs_portal/`` directory cobtains code relating to the interactive, Globus Search-based portal, that provides for visualizing the results from successful XPCS flows and for starting reprocessing flows for datasets published to the portal. See the [Portal README](./xpcs_portal/README.md) for more information on running the portal.


## Online Processing

The [`gladier_xpcs/flows/flow_eigen.py`](https://github.com/globus-gladier/gladier-xpcs/blob/main/gladier_xpcs/flows/flow_eigen.py) program uses the Gladier Toolkit to define a flow with the following sequence of **Transfer**, **Compute**, and **Search** actions:

1. **Transfer** experiment data file from instrument to HPC (tool [`gladier_xpcs/tools/transfer_from_clutch_to_theta.py`](https://github.com/globus-gladier/gladier-xpcs/blob/main/gladier_xpcs/tools/transfer_from_clutch_to_theta.py))
1. **Compute** task to extract metadata from experiment data file (tool [`gladier_xpcs/tools/pre_publish.py`](https://github.com/globus-gladier/gladier-xpcs/blob/main/gladier_xpcs/tools/pre_publish.py))
1. **Transfer** metadata to persistent storage (also tool [`gladier_xpcs/tools/pre_publish.py`](https://github.com/globus-gladier/gladier-xpcs/blob/main/gladier_xpcs/tools/pre_publish.py))
1. **Search** task to load metadata into catalog (also tool [`gladier_xpcs/tools/pre_publish.py`](https://github.com/globus-gladier/gladier-xpcs/blob/main/gladier_xpcs/tools/pre_publish.py))
1. **Compute** task to preallocate nodes on HPC resource (tool [`gladier_xpcs/tools/acquire_nodes.py`](https://github.com/globus-gladier/gladier-xpcs/blob/main/gladier_xpcs/tools/acquire_nodes.py))
1. **Compute** task to run XPCS Boost correlation analysis function on data (tool [`gladier_xpcs/tools/eigen_corr.py`](https://github.com/globus-gladier/gladier-xpcs/blob/main/gladier_xpcs/tools/eigen_corr.py))
1. **Compute** task to create correlation plots (tool [`gladier_xpcs/tools/plot.py`](https://github.com/globus-gladier/gladier-xpcs/blob/main/gladier_xpcs/tools/plot.py))
1. **Compute** task to extract metadata from correlation plots (tool [`gladier_xpcs/tools/gather_xpcs_metadata.py`](https://github.com/globus-gladier/gladier-xpcs/blob/main/gladier_xpcs/tools/gather_xpcs_metadata.py))
1. **Compute** task to aggregate new data, metadata for publication (tool [`gladier_xpcs/tools/publish.py`](https://github.com/globus-gladier/gladier-xpcs/blob/main/gladier_xpcs/tools/publish.py))
1. **Transfer** data+metadata to repository (also tool [`gladier_xpcs/tools/publish.py`](https://github.com/globus-gladier/gladier-xpcs/blob/main/gladier_xpcs/tools/publish.py))
1. **Search** task to add metadata+data references to catalog (also tool [`gladier_xpcs/tools/publish.py`](https://github.com/globus-gladier/gladier-xpcs/blob/main/gladier_xpcs/tools/publish.py))

A script `scripts/xpcs_corr_client.py` can be used to run the flow with specified inputs.

The flow's Compute tasks involve both simple data manipulations (e.g., metadata extraction) and compute-intensive computations (XPCS Boost). On an HPC system, the former may be run on a "non-compute" (front-end) node, while the latter must be submitted via a scheduler to run on a "compute" node (ideally GPU-enabled). To this end, the flow dispatches each task to the `funcx_endpoint_non_compute` or `funcx_endpoint_compute` funcX endpoint, respectively, as defined in [`gladier_xpcs/deployments.py`](https://github.com/globus-gladier/gladier-xpcs/blob/main/gladier_xpcs/deployments.py). 
        
Details on how to run the online processing script on an APS beamline computer, talc, are [provided on a separate page](https://github.com/globus-gladier/gladier-xpcs/blob/main/scripts/online-processing.md). 

## Reprocessing

XPCS Reprocessing takes data already published in the portal and re-processes with
a customized (with a qmap file) HDF file. It also involves an extra step to rename
the reprocessed dataset so as to publish it under a different title in the portal. 

Although scripts exist here to test the reprocessing flow, the actual production flow is
deployed separately on the portal. The portal installs the `gladier_xpcs` package and
imports the Gladier Client.

The main reprocessing client is at `gladier_xpcs/client_reprocess.py`. A script for 
testing reprocessing is located at `scripts/xpcs_reproc_client.py`. Reprocessing
shares some tools with the online processing flow, but contains a handful of custom
tools under `gladier_xpcs/reprocessing_tools`.

### Running The Reprocessing Flow

You need to setup your deployment on Theta before you can run reprocessing. This includes
setting up:

* 'login' and 'compute' funcC endpoints on theta
* a 'processing' directory on theta to which you have read/write access

Make sure you are also in the XPCS Developers Globus group to access XPCS datasets which
have already been published.

To test a reprocessing flow, run the following:

```
cd scripts/
python xpcs_reproc_client.py
```

### ALCF Configuration

Hopefully, this document is a little outdated and you're executing on Polaris!
Please add, update, or correct information as things change. 

## FuncX Endpoint Setup

```
  conda create -n xpcs-polaris python=3.9
  conda activate xpcs-polaris
  conda install -c nvidia cudatoolkit
  conda install -c pytorch pytorch

  pip install funcx-endpoint
  pip install -e git+https://github.com/AZjk/boost_corr#egg=boost_corr
  pip install -e git+https://github.com/AZjk/xpcs_webplot#egg=xpcs_webplot
```

### Example Config

```
~/.funcx/theta/config.py

from parsl.addresses import address_by_hostname
from parsl.launchers import AprunLauncher, SingleNodeLauncher
from parsl.providers import CobaltProvider, PBSProProvider
from funcx_endpoint.endpoint.utils.config import Config
from funcx_endpoint.executors import HighThroughputExecutor
from funcx_endpoint.strategies import SimpleStrategy

user_opts = {
    'polaris': {
        'worker_init': 'export PATH="/home/nicks/miniconda3/envs/gladier-xpcs/bin:$PATH"; source activate gladier-xpcs',
        # PBS directives (header lines): for array jobs pass '-J' option
        'scheduler_options': ''
    }
}

config = Config(
    executors=[
        HighThroughputExecutor(
            max_workers_per_node=1,
            strategy=SimpleStrategy(max_idletime=600),
            address=address_by_hostname(),
            provider=PBSProProvider(
                cpus_per_node=32,
                select_options="ngpus=4",
                launcher=SingleNodeLauncher(),
                account='APSDataAnalysis',
                queue='preemptable',
                scheduler_options=user_opts['polaris']['scheduler_options'],
                worker_init=user_opts['polaris']['worker_init'],
                walltime='10:00:00',
                nodes_per_block=1,
                init_blocks=0,
                min_blocks=0,
                max_blocks=10,
            ),
        )
    ],
)
```
