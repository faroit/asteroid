"""
Proposed base class to interface with pytorch-lightning.
@author : Manuel Pariente, Inria-Nancy
"""

import torch
import pytorch_lightning as pl


class System(pl.LightningModule):
    """ Base class for deep learning systems.
    Subclass of pytorch_lightning.LightningModule.
    Contains a model, an optimizer, a loss_class and training and validation
    loaders and learning rate scheduler.

    Args:
        model (torch.nn.Module): Instance of model.
        optimizer (torch.optim.Optimizer): Instance or list of optimizers.
        loss_class: Class with `compute` method. (More doc to come)
        train_loader (torch.utils.data.DataLoader): Training dataloader.
        val_loader (torch.utils.data.DataLoader): Validation dataloader.
        scheduler (torch.optim._LRScheduler): Instance, or list.
        config: Anything to be saved with the checkpoints during training.
            The config dictionary to re-instantiate the run for example.

    By default, `training_step` (used by pytorch-lightning in the training
    loop) and `validation_step` (used for the validation loop) share
    `common_step`. If you want different behavior for the training loop and
    the validation loop, overwrite both `training_step` and `validation_step`
    instead.
    """
    def __init__(self, model, optimizer, loss_class, train_loader,
                 val_loader=None, scheduler=None, config=None):
        super().__init__()
        self.model = model
        self.optimizer = optimizer
        self.loss_class = loss_class
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.scheduler = scheduler
        self.config = config

    def forward(self, *args, **kwargs):
        """ Applies forward pass.

        Required by PL.

        Returns:
            :class:`torch.Tensor`
        """
        return self.model.forward(*args, **kwargs)

    def common_step(self, batch, batch_nb):
        """ Common forward step between training and validation.

        The function of this method is to unpack the data given by the loader,
        forward the batch through the model and compute the loss.

        Args:
            batch: the object returned by the loader (a list of torch.Tensor
                in most cases) but can be something else.
            batch_nb (int): The number of the batch in the epoch.

        Returns:
            float: The loss value on this batch.

        .. note:: This is typically the method to overwrite when subclassing
            `System`. If the training and validation steps are different
            (except for loss.backward() and optimzer.step()), then overwrite
            `training_step` and `validation_step` instead.
        """
        inputs, targets, infos = self.unpack_data(batch)
        est_targets = self.model(inputs)
        loss = self.loss_class.compute(targets, est_targets, infos=infos)
        return loss

    def unpack_data(self, data):
        """ Unpack data given by the DataLoader

        Args:
            data: list of 2 or 3 elements.
                [model_inputs, training_targets, additional infos] or
                [model_inputs, training_targets]

        Returns:
              model_inputs, training_targets, additional infos
        """
        if len(data) == 2:
            inputs, targets = data
            infos = dict()
        elif len(data) == 3:
            inputs, targets, infos = data
        else:
            raise ValueError('Expected DataLoader output to have '
                             '2 or 3 elements. Received '
                             '{} elements'.format(len(data)))
        return inputs, targets, infos

    def training_step(self, batch, batch_nb):
        """ Pass data through the model and compute the loss.

        Backprop is **not** performed.

        Args:
            batch: the object returned by the loader (a list of torch.Tensor
                in most cases) but can be something else.
            batch_nb (int): The number of the batch in the epoch.

        Returns:
            dict:

            ``'loss'``: loss

            ``'log'``: dict with tensorboard logs

        """
        loss = self.common_step(batch, batch_nb)
        tensorboard_logs = {'train_loss': loss}
        return {'loss': loss, 'log': tensorboard_logs}

    def validation_step(self, batch, batch_nb):
        """ Need to overwrite PL validation_step to do validation.

        Args:
            batch: the object returned by the loader (a list of torch.Tensor
                in most cases) but can be something else.
            batch_nb (int): The number of the batch in the epoch.

        Returns:
            dict:

            ``'val_loss'``: loss
        """
        loss = self.common_step(batch, batch_nb)
        return {'val_loss': loss}

    def validation_end(self, outputs):
        """ How to aggregate outputs of `validation_step` for logging.

        Args:
           outputs (List[dict]): List of validation losses, each with a
           ``'val_loss'`` key

        Returns:
            dict: Average loss

            ``'val_loss'``: Average loss on `outputs`

            ``'log'``: Tensorboard logs

            ``'progress_bar'``: Tensorboard logs
        """
        avg_loss = torch.stack([x['val_loss'] for x in outputs]).mean()
        tensorboard_logs = {'val_loss': avg_loss}
        return {'val_loss': avg_loss, 'log': tensorboard_logs,
                'progress_bar': tensorboard_logs}

    def configure_optimizers(self):
        """ Required by pytorch-lightning. """
        if self.scheduler is not None:
            return self.optimizer, self.scheduler
        return self.optimizer

    @pl.data_loader
    def train_dataloader(self):
        return self.train_loader

    @pl.data_loader
    def val_dataloader(self):
        return self.val_loader

    def on_save_checkpoint(self, checkpoint):
        """ Overwrite if you want to save more things in the checkpoint."""
        checkpoint['training_config'] = self.config
        return checkpoint

    def on_batch_start(self, batch):
        """ Overwrite if needed. Called by pytorch-lightning"""
        pass

    def on_batch_end(self):
        """ Overwrite if needed. Called by pytorch-lightning"""
        pass

    def on_epoch_start(self):
        """ Overwrite if needed. Called by pytorch-lightning"""
        pass

    def on_epoch_end(self):
        """ Overwrite if needed. Called by pytorch-lightning"""
        pass

    @pl.data_loader
    def tng_dataloader(self):
        """ Deprecated."""
        pass
