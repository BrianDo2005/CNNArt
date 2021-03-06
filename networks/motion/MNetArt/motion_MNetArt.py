import os.path
import scipy.io as sio
import keras
import keras.optimizers
from keras.models import Sequential, Model
from keras.layers import Input
from keras.layers.core import Dense, Activation, Flatten,   Dropout, Lambda, Reshape, Permute
from keras.activations import relu, elu, softmax
from keras.layers.advanced_activations import LeakyReLU, PReLU
from keras.initializers import Constant
from keras.layers import  concatenate, add
from keras.layers.convolutional import Conv3D,Conv2D, MaxPooling3D, MaxPooling2D, ZeroPadding3D
from keras.regularizers import l1_l2,l2
from keras.models import model_from_json
from keras.callbacks import EarlyStopping, ModelCheckpoint,ReduceLROnPlateau

def fTrain(sOutPath, patchSize,sInPaths=None,sInPaths_valid=None,X_train=None, Y_train=None, X_test=None, Y_test=None, CV_Patient=0, model='motion_head'):#rigid for loops for simplicity
    #add for loops here
    learning_rate = 0.001
    cnn, sModelName= fCreateModel(patchSize, learningRate=learning_rate, optimizer='Adam')
    print("Modelname:" + sModelName)
    fTrainInner(sOutPath, cnn, sModelName, X_train=X_train, Y_train=Y_train, X_test=X_test, Y_test=Y_test,CV_Patient=CV_Patient,
         batchSize=64, iEpochs=300)


def fTrainInner(sOutPath, model, sModelName, patchSize=None, sInPaths=None, sInPaths_valid=None, X_train=None, Y_train=None, X_test=None, Y_test=None,  batchSize=64, iEpochs=299, CV_Patient=0):
    '''train a model with training data X_train with labels Y_train. Validation Data should get the keywords Y_test and X_test'''

    print('Training CNN')
    print('with '  + 'batchSize = ' + str(batchSize))

    # save names
    _, sPath = os.path.splitdrive(sOutPath)
    sPath, sFilename = os.path.split(sPath)
    sFilename, sExt = os.path.splitext(sFilename)

    model_name = sPath + '/' + sModelName + '_bs:{}'.format(batchSize)
    if CV_Patient != 0: model_name = model_name +'_'+ 'CV' + str(CV_Patient)# determine if crossValPatient is used...
    weight_name = model_name + '_weights.h5'
    model_json = model_name + '_json'
    model_all = model_name + '_model.h5'
    model_mat = model_name + '.mat'

    if (os.path.isfile(model_mat)):  # no training if output file exists
        print('----------already trained->go to next----------')
        return


    callbacks = [EarlyStopping(monitor='val_loss', patience=10, verbose=1)]
    callbacks.append(ModelCheckpoint('/home/s1222/no_backup/s1222/checkpoints/checker.hdf5', monitor='val_acc', verbose=0,
        period=5, save_best_only=True))# overrides the last checkpoint, its just for security
    callbacks.append(ReduceLROnPlateau(monitor='loss', factor=0.5, patience=5, min_lr=1e-4, verbose=1))

    result =model.fit(X_train,
                         Y_train,
                         validation_data=[X_test, Y_test],
                         epochs=iEpochs,
                         batch_size=batchSize,
                         callbacks=callbacks,
                         verbose=1)

    print('\nscore and acc on test set:')
    score_test, acc_test = model.evaluate(X_test, Y_test, batch_size=batchSize, verbose=1)
    print('\npredict class probabillities:')
    prob_test = model.predict(X_test, batchSize, verbose=1)

    # save model
    json_string = model.to_json()
    open(model_json +'.txt', 'w').write(json_string)

    model.save_weights(weight_name, overwrite=True)


    # matlab
    acc = result.history['acc']
    loss = result.history['loss']
    val_acc = result.history['val_acc']
    val_loss = result.history['val_loss']


    print('\nSaving results: ' + model_name)
    sio.savemat(model_name, {'model_settings': model_json,
                             'model': model_all,
                             'weights': weight_name,
                             'acc_history': acc,
                             'loss_history': loss,
                             'val_acc_history': val_acc,
                             'val_loss_history': val_loss,
                             'loss_test': score_test,
                             'acc_test': acc_test,
                             'prob_test': prob_test})

def fPredict(X,y,  sModelPath, sOutPath, batchSize=64):
    """Takes an already trained model and computes the loss and Accuracy over the samples X with their Labels y
    Input:
        X: Samples to predict on. The shape of X should fit to the input shape of the model
        y: Labels for the Samples. Number of Samples should be equal to the number of samples in X
        sModelPath: (String) full path to a trained keras model. It should be *_json.txt file. there has to be a corresponding *_weights.h5 file in the same directory!
        sOutPath: (String) full path for the Output. It is a *.mat file with the computed loss and accuracy stored. 
                    The Output file has the Path 'sOutPath'+ the filename of sModelPath without the '_json.txt' added the suffix '_pred.mat' 
        batchSize: Batchsize, number of samples that are processed at once"""
    sModelPath= sModelPath.replace("_json.txt", "")
    weight_name = sModelPath + '_weights.h5'
    model_json = sModelPath + '_json.txt'
    model_all = sModelPath + '_model.h5'

    # load weights and model (new way)
    model_json= open(model_json, 'r')
    model_string=model_json.read()
    model_json.close()
    model = model_from_json(model_string)

    model.compile(loss='categorical_crossentropy',optimizer=keras.optimizers.Adam(), metrics=['accuracy'])
    model.load_weights(weight_name)


    score_test, acc_test = model.evaluate(X, y, batch_size=batchSize)
    print('loss'+str(score_test)+ '   acc:'+ str(acc_test))
    prob_pre = model.predict(X, batch_size=batchSize, verbose=1)
    print(prob_pre[0:14,:])
    _,sModelFileSave  = os.path.split(sModelPath)

    modelSave = sOutPath +sModelFileSave+ '_pred.mat'
    print('saving Model:{}'.format(modelSave))
    sio.savemat(modelSave, {'prob_pre': prob_pre, 'score_test': score_test, 'acc_test': acc_test})

def fCreateModel(patchSize, learningRate=1e-3, optimizer='SGD',
        dr_rate=0.0, input_dr_rate=0.0, max_norm=5, iPReLU=0, l2_reg=1e-6):
        l2_reg=1e-4

        #(4 stages-each 2 convs)(378,722 params)(for 40x40x10)
        input_t=Input(shape=(1,int(patchSize[0, 0]),int(patchSize[0, 1]), int(patchSize[0, 2])))
        input2D_t=Permute((4,1,2,3))(input_t)
        input2D_t=Reshape(target_shape=(int(patchSize[0, 2]),int(patchSize[0, 0]), int(patchSize[0, 1])))(
            input2D_t)
        #use zDimension as number of channels
        twoD_t=Conv2D(16,
                      kernel_size=(7,7),
                      padding='same',
                      kernel_initializer='he_normal',
                      kernel_regularizer=l2(l2_reg),
                      strides=(1,1)
                      )(input2D_t)
        twoD_t = Activation('relu')(twoD_t)

        l_w2_t = fCreateMaxPooling2D(twoD_t, stride=(2, 2))
        l_w3_t = fCreateMaxPooling2D(l_w2_t, stride=(2, 2))
        l_w4_t = fCreateMaxPooling2D(l_w3_t, stride=(2, 2))

        stage1_res1_t=fCreateMNet_Block(twoD_t,16,kernel_size=(3,3), forwarding=True, l2_reg=l2_reg)
        stage1_res2_t=fCreateMNet_Block(stage1_res1_t,32,kernel_size=(3,3), forwarding=False, l2_reg=l2_reg)

        stage2_inp_t=fCreateMaxPooling2D(stage1_res2_t, stride=(2,2))
        stage2_inp_t=concatenate([stage2_inp_t,l_w2_t], axis=1)
        stage2_res1_t=fCreateMNet_Block(stage2_inp_t,32,l2_reg=l2_reg)
        stage2_res2_t=fCreateMNet_Block(stage2_res1_t,48, forwarding=False)

        stage3_inp_t=fCreateMaxPooling2D(stage2_res2_t, stride=(2,2))
        stage3_inp_t=concatenate([stage3_inp_t,l_w3_t], axis=1)
        stage3_res1_t=fCreateMNet_Block(stage3_inp_t,48,l2_reg=l2_reg)
        stage3_res2_t = fCreateMNet_Block(stage3_res1_t, 64, forwarding=False,l2_reg=l2_reg)

        stage4_inp_t = fCreateMaxPooling2D(stage3_res2_t, stride=(2, 2))
        stage4_inp_t = concatenate([stage4_inp_t, l_w4_t], axis=1)
        stage4_res1_t = fCreateMNet_Block(stage4_inp_t, 64,l2_reg=l2_reg)
        stage4_res2_t = fCreateMNet_Block(stage4_res1_t, 128, forwarding=False,l2_reg=l2_reg)

        after_flat_t = Flatten()(stage4_res2_t)

        after_dense_t = Dense(units=2,
                              kernel_initializer='he_normal',
                              kernel_regularizer=l2(l2_reg))(after_flat_t)
        output_t = Activation('softmax')(after_dense_t)

        cnn = Model(inputs=[input_t], outputs=[output_t])

        opti, loss = fGetOptimizerAndLoss(optimizer, learningRate=learningRate)
        cnn.compile(optimizer=opti, loss=loss, metrics=['accuracy'])
        sArchiSpecs = '3stages_l2{}'.format(l2_reg)


def fGetOptimizerAndLoss(optimizer,learningRate=0.001, loss='categorical_crossentropy'):
    if optimizer not in ['Adam', 'SGD', 'Adamax', 'Adagrad', 'Adadelta', 'Nadam', 'RMSprop']:
        print('this optimizer does not exist!!!')
        return None
    loss='categorical_crossentropy'

    if optimizer == 'Adamax':  # leave the rest as default values
        opti = keras.optimizers.Adamax(lr=learningRate)
        loss = 'categorical_crossentropy'
    elif optimizer == 'SGD':
        opti = keras.optimizers.SGD(lr=learningRate, momentum=0.9, decay=5e-5)
        loss = 'categorical_crossentropy'
    elif optimizer == 'Adagrad':
        opti = keras.optimizers.Adagrad(lr=learningRate)
    elif optimizer == 'Adadelta':
        opti = keras.optimizers.Adadelta(lr=learningRate)
    elif optimizer == 'Adam':
        opti = keras.optimizers.Adam(lr=learningRate, decay=5e-5)
        loss = 'categorical_crossentropy'
    elif optimizer == 'Nadam':
        opti = keras.optimizers.Nadam(lr=learningRate)
        loss = 'categorical_crossentropy'
    elif optimizer == 'RMSprop':
        opti = keras.optimizers.RMSprop(lr=learningRate)
    return opti, loss

def fCreateMaxPooling2D(input_t,stride=(2,2)):
    output_t=MaxPooling2D(pool_size=stride,
                          strides=stride,
                          padding='valid')(input_t)
    return output_t



def fCreateMNet_Block(input_t, channels, kernel_size=(3,3), type=1, forwarding=True,l1_reg=0.0, l2_reg=1e-6 ):
    tower_t = Conv2D(channels,
                     kernel_size=kernel_size,
                     kernel_initializer='he_normal',
                     weights=None,
                     padding='same',
                     strides=(1, 1),
                     kernel_regularizer=l1_l2(l1_reg, l2_reg),
                     )(input_t)
    tower_t = Activation('relu')(tower_t)
    for counter in range(1, type):
        tower_t = Conv2D(channels,
                         kernel_size=kernel_size,
                         kernel_initializer='he_normal',
                         weights=None,
                         padding='same',
                         strides=(1, 1),
                         kernel_regularizer=l1_l2(l1_reg, l2_reg),
                         )(tower_t)
        tower_t = Activation('relu')(tower_t)
    if (forwarding):
        tower_t = concatenate([tower_t, input_t], axis=1)
    return tower_t


