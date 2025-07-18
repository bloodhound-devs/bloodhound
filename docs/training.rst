================================
Training
================================

Once you have :doc:`preprocessed <preprocessing>` the dataset, you can train the model.

Small Model 
================================

Here is an example to train the model with the default parameters which results in the small Barbet model.

.. code-block:: bash

    LAYERS=6
    barbet-tools train  \
        --memmap  preprocessed/esm${LAYERS}.npy \
        --memmap-index  preprocessed/esm${LAYERS}.txt \
        --treedict  preprocessed/esm${LAYERS}.st \
        --max-learning-rate 0.0002 \
        --max-epochs 70 \
        --train-all \
        --embedding-model ESM${LAYERS} \
        --run-name "Barbet-ESM${LAYERS}-small"

This will create a model in the ``logs/Barbet-ESM6-small`` directory. The checkpoint with the weights will be saved in the directory called:
``logs/Barbet-ESM6-small/version_0/checkpoints/``. Use the smaller checkpoint with the ``weights`` prefix. 
The larger checkpoint with the ``checkpoint`` prefix includes optimizer state and you can delete this file once the training is finished.

If you want to use Weights and Biases for logging, you can add the ``--wandb`` option to the command.

Large Model 
================================

If you want to train the large Barbet model, you can use the following command:

.. code-block:: bash

    LAYERS=6
    barbet-tools train  \
        --memmap  preprocessed/esm${LAYERS}.npy \
        --memmap-index  preprocessed/esm${LAYERS}.txt \
        --treedict  preprocessed/esm${LAYERS}.st \
        --features 1536 \
        --max-learning-rate 0.0002 \
        --max-epochs 70 \
        --train-all \
        --embedding-model ESM${LAYERS} \
        --run-name "Barbet-ESM${LAYERS}-large"


Advanced Training
================================

See more options for training with the command:

.. code-block:: bash

    barbet-tools train --help