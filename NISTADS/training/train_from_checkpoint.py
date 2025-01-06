# [SET KERAS BACKEND]
import os 
os.environ["KERAS_BACKEND"] = "torch"

# [SETTING WARNINGS]
import warnings
warnings.simplefilter(action='ignore', category=Warning)

# [IMPORT CUSTOM MODULES]
from NISTADS.commons.utils.dataloader.generators import ML_model_dataloader
from NISTADS.commons.utils.dataloader.serializer import DataSerializer, ModelSerializer
from NISTADS.commons.utils.models.training import ModelTraining
from NISTADS.commons.constants import CONFIG, DATA_PATH
from NISTADS.commons.logger import logger


# [RUN MAIN]
###############################################################################
if __name__ == '__main__':

    # 1. [LOAD PRETRAINED MODEL]
    #--------------------------------------------------------------------------    
    dataserializer = DataSerializer()   
    modelserializer = ModelSerializer() 

    # setting device for training    
    trainer = ModelTraining()
    trainer.set_device()    
    
    # selected and load the pretrained model, then print the summary     
    logger.info('Loading specific checkpoint from pretrained models')   
    model, parameters = modelserializer.select_and_load_checkpoint()
    checkpoint_path = modelserializer.loaded_model_folder
    model.summary(expand_nested=True)      

    # 2. [DEFINE IMAGES GENERATOR AND BUILD TF.DATASET]
    #--------------------------------------------------------------------------
    # initialize training device, allows changing device prior to initializing the generators
    #--------------------------------------------------------------------------   
    # load saved tf.datasets from the proper folders in the checkpoint directory     
    train_data, validation_data = dataserializer.load_preprocessed_data(checkpoint_path)

    # initialize the TensorDataSet class with the generator instances
    # create the tf.datasets using the previously initialized generators   
    logger.info('Building data loaders') 
    train_dataset, validation_dataset = ML_model_dataloader(train_data, validation_data)
    
    # 3. [TRAINING MODEL]  
    #--------------------------------------------------------------------------  
    # Setting callbacks and training routine for the features extraction model 
    # use command prompt on the model folder and (upon activating environment), 
    # use the bash command: python -m tensorboard.main --logdir tensorboard/ 
    #--------------------------------------------------------------------------
    logger.info('--------------------------------------------------------------')
    logger.info('FeXT resume training report')
    logger.info('--------------------------------------------------------------')    
    logger.info(f'Number of train samples:       {len(train_data)}')
    logger.info(f'Number of validation samples:  {len(validation_data)}')      
    logger.info(f'Picture shape:                 {CONFIG["model"]["IMG_SHAPE"]}')   
    logger.info(f'Batch size:                    {CONFIG["training"]["BATCH_SIZE"]}')
    logger.info(f'Epochs:                        {CONFIG["training"]["EPOCHS"]}')  
    logger.info('--------------------------------------------------------------\n')      

    # resume training from pretrained model
    session_index = parameters['session_ID'] + 1
    trainer.train_model(model, train_dataset, validation_dataset, checkpoint_path,
                        from_epoch=parameters['epochs'], session_index=session_index)



