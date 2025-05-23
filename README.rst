.. image:: https://github.com/bloodhound-devs/bloodhound/blob/main/docs/images/bloodhound-banner.jpg?raw=true

.. start-badges

|testing badge| |coverage badge| |docs badge| |black badge| |torchapp badge|

.. |testing badge| image:: https://github.com/bloodhound-devs/bloodhound/actions/workflows/testing.yml/badge.svg
    :target: https://github.com/bloodhound-devs/bloodhound/actions

.. |docs badge| image:: https://github.com/bloodhound-devs/bloodhound/actions/workflows/docs.yml/badge.svg
    :target: https://bloodhound-devs.github.io/bloodhound
    
.. |black badge| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
    
.. |coverage badge| image:: https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/rbturnbull/09aad5114164b54daabe1f5efd02a009/raw/coverage-badge.json
    :target: https://bloodhound-devs.github.io/bloodhound/coverage/

.. |torchapp badge| image:: https://img.shields.io/badge/MLOpps-torchapp-B1230A.svg
    :target: https://rbturnbull.github.io/torchapp/
    
.. end-badges

.. start-quickstart

Installation
==================================

Install using pip:

.. code-block:: bash

    pip install git+https://github.com/bloodhound-devs/bloodhound.git


Usage
==================================

See the options for making inferences with the command:

.. code-block:: bash

    bloodhound --help

Model
==================================

.. code-block:: bash

    wget https://figshare.com/ndownloader/files/54720671?private_link=5f43c8fc6f157f3111e3 -O bloodhound.zip
    unzip bloodhound.zip

Run
==================================

.. code-block:: bash

    bloodhound --checkpoint bloodhound.r226.ckpt --hmm-models-dir markers --output-csv GCA_000006945.csv --input GCA_000006945.2.fna


Training
==================================

You can train the model on releases from GTDB or your own custom dataset.
See the instructions in the documentation for `preprocessing <https://bloodhound-devs.github.io/bloodhound/preprocessing.html>`_ and `training <https://bloodhound-devs.github.io/bloodhound/training.html>`_.

.. end-quickstart


Credits
==================================

.. start-credits

Robert Turnbull, Mar Quiroga, Gabriele Marini, Torsten Seemann,  Wytamma Wirth

For more information contact: <wytamma.wirth@unimelb.edu.au>

Created using torchapp (https://github.com/rbturnbull/torchapp).

.. end-credits

