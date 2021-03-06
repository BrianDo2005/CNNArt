'''
@author: Yannick Wilhelm
@email: yannick.wilhelm@gmx.de
@date: January 2018
'''

import sys

from utilsGUI.RigidPatching import *
from utilsGUI.DataPreprocessing import *
from utilsGUI.Training_Test_Split import *
import scipy.io as sio

import os

from Dataset import Dataset
from utilsGUI.Label import Label
import tensorflow as tf
import numpy as np
import dicom as dicom
import dicom_numpy as dicom_np
import json
import datetime
import h5py

import cnn_main

# ArtGAN
# from ArtGAN import artGAN_main as artGAN

class DeepLearningArtApp():
    datasets = {
        't1_tse_tra_Kopf_0002': Dataset('t1_tse_tra_Kopf_0002', None,'ref', 'head', 't1'),
        't1_tse_tra_Kopf_Motion_0003': Dataset('t1_tse_tra_Kopf_Motion_0003', None, 'motion','head', 't1'),
        't1_tse_tra_fs_mbh_Leber_0004': Dataset('t1_tse_tra_fs_mbh_Leber_0004',None,'ref','abdomen', 't1'),
        't1_tse_tra_fs_mbh_Leber_Motion_0005': Dataset('t1_tse_tra_fs_mbh_Leber_Motion_0005', None, 'motion', 'abdomen', 't1'),
        't2_tse_tra_fs_navi_Leber_0006': Dataset('t2_tse_tra_fs_navi_Leber_0006',None,'ref','abdomen', 't2'),
        't2_tse_tra_fs_navi_Leber_Shim_xz_0007': Dataset('t2_tse_tra_fs_navi_Leber_Shim_xz_0007', None, 'shim', 'abdomen', 't2'),
        't1_tse_tra_fs_Becken_0008': Dataset('t1_tse_tra_fs_Becken_0008', None, 'ref', 'pelvis', 't1'),
        't2_tse_tra_fs_Becken_0009': Dataset('t2_tse_tra_fs_Becken_0009', None, 'ref', 'pelvis', 't2'),
        't1_tse_tra_fs_Becken_Motion_0010': Dataset('t1_tse_tra_fs_Becken_Motion_0010', None, 'motion', 'pelvis', 't1'),
        't2_tse_tra_fs_Becken_Motion_0011': Dataset('t2_tse_tra_fs_Becken_Motion_0011', None, 'motion', 'pelvis', 't2'),
        't2_tse_tra_fs_Becken_Shim_xz_0012': Dataset('t2_tse_tra_fs_Becken_Shim_xz_0012', None, 'shim', 'pelvis', 't2')
    }

    deepNeuralNetworks = {
        'Multiclass DenseResNet': 'networks.multiclass.DenseResNet.multiclass_DenseResNet',
        'Multiclass InceptionNet': 'networks.multiclass.InceptionNet.multiclass_InceptionNet',
        'Mulitclass ResNet-56': 'networks.multiclass.SENets.multiclass_ResNet-56',
        'Multiclass SE-ResNet-56': 'networks.multiclass.SENets.multiclass_SE-ResNet-56',
        'Mulitclass ResNet-50': 'networks.multiclass.SENets.multiclass_ResNet-50',
        'Multiclass SE-ResNet-50': 'networks.multiclass.SENets.multiclass_SE-ResNet-50',
        'Multiclass DenseNet-34': 'networks.multiclass.SENets.multiclass_DenseNet-34',
        'Multiclass SE-DenseNet-34': 'networks.multiclass.SENets.multiclass_SE-DenseNet-34',
        'Multiclass DenseNet-BC-100': 'networks.multiclass.SENets.multiclass_DenseNet-BC-100',
        'Multiclass SE-DenseNet-BC-100': 'networks.multiclass.SENets.multiclass_SE-DenseNet-BC-100',
        'Multiclass SE-ResNet-32': 'networks.multiclass.SENets.multiclass_SE-ResNet-32',
        'Multiclass 3D ResNet': 'networks.multiclass.CNN3D.multiclass_3D_ResNet',
        'Multiclass 3D SE-ResNet': 'networks.multiclass.CNN3D.multiclass_3D_SE-ResNet',
        'Multiclass SE-ResNet-44_dense': 'networks.multiclass.SENets.multiclass_SE-ResNet-44_dense',
        'FCN 3D-VResFCN': 'networks.FullyConvolutionalNetworks.3D_VResFCN',
        'FCN 3D-VResFCN-Upsampling': 'networks.FullyConvolutionalNetworks.3D_VResFCN_Upsampling',
        'FCN 3D-VResFCN-Upsampling small': 'networks.FullyConvolutionalNetworks.3D_VResFCN_Upsampling_small'
    }

    modelSubDir = "dicom_sorted"

    # constants labeling modes
    MASK_LABELING = 0
    PATCH_LABELING = 1

    # constants patching modes
    PATCHING_2D = 0
    PATCHING_3D = 1

    # constants splitting modes
    NONE_SPLITTING = 0
    SIMPLE_RANDOM_SAMPLE_SPLITTING = 1
    CROSS_VALIDATION_SPLITTING = 2
    PATIENT_CROSS_VALIDATION_SPLITTING = 3

    # constants storage mode
    STORE_DISABLED = 0
    STORE_HDF5 = 1
    STORE_PATCH_BASED = 2

    # optimizer constants
    SGD_OPTIMIZER = 0
    RMS_PROP_OPTIMIZER = 1
    ADAGRAD_OPTIMIZER = 2
    ADADELTA_OPTIMIZER = 3
    ADAM_OPTIMIZER = 4

    # Data Augmentation Parameters
    WIDTH_SHIFT_RANGE = 0.2
    HEIGHT_SHIFT_RANGE = 0.2
    ROTATION_RANGE = 30
    ZOOM_RANGE = 0.2


    def __init__(self):
        # GUI handle
        self.dlart_GUI_handle = None

        # attributes for paths and database
        self.selectedPatients = ''
        self.selectedDatasets = ''

        self.pathDatabase, self.pathOutputPatching, self.markingsPath, self.learningOutputPath, self.pathOutputPatchingGAN \
                = DeepLearningArtApp.getOSPathes(operatingSystem=0)  # for windows os=0, for linse server os=1. see method for pathes

        # attributes for patching
        self.patchSizeX = 40
        self.patchSizeY = 40
        self.patchSizeZ = 5
        self.patchOverlapp = 0.6

        self.usingSegmentationMasks = False

        #attributes for labeling
        self.labelingMode = ''

        #attributes for patching
        self.patchingMode = DeepLearningArtApp.PATCHING_2D
        self.storeMode = ''

        # attributes for splitting
        self.datasetName = 'none'
        self.splittingMode = DeepLearningArtApp.SIMPLE_RANDOM_SAMPLE_SPLITTING
        self.trainTestDatasetRatio = 0.2 #part of test data
        self.trainValidationRatio = 0.2 # part of Validation data in traindata
        self.numFolds = 5

        ################################################################################################################
        #attributes for DNN and Training
        ################################################################################################################
        self.neuralNetworkModel = None
        self.batchSizes = None
        self.epochs = None
        self.learningRates = None

        self.optimizer = DeepLearningArtApp.SGD_OPTIMIZER
        self.weightDecay = 0.0001
        self.momentum = 0.9
        self.nesterovEnabled = False

        self.dataAugmentationEnabled = False
        self.horizontalFlip = True
        self.verticalFlip = False
        self.rotation = 0
        self.zcaWhitening = False
        self.heightShift = 0
        self.widthShift = 0
        self.zoom = 0
        self.contrastStretching = False
        self.adaptive_eq = False
        self.histogram_eq = False
        ################################################################################################################


        # Attributes for classes and labels
        self.usingArtifacts = True
        self.usingBodyRegions = True
        self.usingTWeighting = True

        # train, validation, test dataset attributes
        self.X_train = None
        self.Y_train = None
        self.Y_segMasks_train = None

        self.X_validation = None
        self.Y_validation = None
        self.Y_segMasks_validation = None

        self.X_test = None
        self.Y_test = None
        self.Y_segMasks_test = None


        ####################
        ### ArtGAN Stuff ###
        ####################
        self.patients_ArtGAN = None
        self.datasets_ArtGAN = None
        self.datasets_ArtGAN_Pairs = None

        self.patchSizeX_ArtGAN = 40
        self.patchSizeY_ArtGAN = 40
        self.patchSizeZ_ArtGAN = 5
        self.patchOverlap_ArtGAN = 0.5

        self.lscaleFactor_ArtGAN = [0.5, 1, 2]

        self.storeMode_ArtGAN = DeepLearningArtApp.STORE_DISABLED
        self.splittingMode_ArtGAN = DeepLearningArtApp.SIMPLE_RANDOM_SAMPLE_SPLITTING

        self.trainTestDatasetRatio_ArtGAN = 0.2  # part of test data
        self.trainValidationRatio_ArtGAN = 0.0  # part of Validation data in traindata
        ####################


    def generateDataset(self):
        '''
        method performs the splitting of the datasets to the learning datasets (training, validation, test)
        and handles the storage of datasets
        :return:
        '''
        self.X_test = []
        self.X_validation= []
        self.X_train = []
        self.Y_test = []
        self.Y_validation = []
        self.Y_train = []

        if self.patchingMode == DeepLearningArtApp.PATCHING_2D:
            dAllPatches = np.zeros((self.patchSizeX, self.patchSizeY, 0))
            dAllLabels = np.zeros(0)
            if self.usingSegmentationMasks:
                dAllSegmentationMaskPatches = np.zeros((self.patchSizeX, self.patchSizeY, 0))
        elif self.patchingMode == DeepLearningArtApp.PATCHING_3D:
            dAllPatches = np.zeros([self.patchSizeX, self.patchSizeY, self.patchSizeZ, 0])
            dAllLabels = np.zeros(0)
            if self.usingSegmentationMasks:
                dAllSegmentationMaskPatches = np.zeros([self.patchSizeX, self.patchSizeY, self.patchSizeZ, 0])
        else:
            raise IOError("We do not know your patching mode...")

        # stuff for storing
        if self.storeMode != DeepLearningArtApp.STORE_DISABLED:
            # outPutFolder name:
            outPutFolder = "Patients-" + str(len(self.selectedPatients)) + "_" + \
                           "Datasets-" + str(len(self.selectedDatasets)) + "_" + \
                           ("2D" if self.patchingMode == DeepLearningArtApp.PATCHING_2D else "3D") + \
                           ('_SegMask_' if self.usingSegmentationMasks else '_') + \
                           str(self.patchSizeX) + "x" + str(self.patchSizeY)
            if self.patchingMode == DeepLearningArtApp.PATCHING_3D:
                outPutFolder = outPutFolder + "x" + str(self.patchSizeZ)\

            outPutFolder = outPutFolder + "_Overlap-" + str(self.patchOverlapp) + "_" + \
                           "Labeling-" + ("patch" if self.labelingMode == DeepLearningArtApp.PATCH_LABELING else "mask")

            if self.splittingMode == DeepLearningArtApp.SIMPLE_RANDOM_SAMPLE_SPLITTING:
                outPutFolder = outPutFolder + "_Split-simpleRand"
            elif self.splittingMode == DeepLearningArtApp.CROSS_VALIDATION_SPLITTING:
                outPutFolder = outPutFolder + "_Split-crossVal"
            elif self.splittingMode == DeepLearningArtApp.SIMPLE_RANDOM_SAMPLE_SPLITTING:
                outPutFolder = outPutFolder + "Split-patientCrossVal"

            outputFolderPath = self.pathOutputPatching + os.sep + outPutFolder

            if not os.path.exists(outputFolderPath):
                os.makedirs(outputFolderPath)

            # create dataset summary
            self.datasetName = outPutFolder
            self.createDatasetInfoSummary(outPutFolder, outputFolderPath)

            if self.storeMode == DeepLearningArtApp.STORE_PATCH_BASED:
                outPutFolderDataPath = outputFolderPath + os.sep + "data"
                if not os.path.exists(outPutFolderDataPath):
                    os.makedirs(outPutFolderDataPath)

                labelDict = {}

        #for storing patch based
        iPatchToDisk = 0

        for patient in self.selectedPatients:
            for dataset in self.selectedDatasets:
                currentDataDir = self.pathDatabase + os.sep + patient + os.sep + self.modelSubDir + os.sep + dataset
                if os.path.exists(currentDataDir):
                    # get list with all paths of dicoms for current patient and current dataset
                    fileNames = os.listdir(currentDataDir)
                    fileNames = [os.path.join(currentDataDir, f) for f in fileNames]

                    # read DICOMS
                    dicomDataset = [dicom.read_file(f) for f in fileNames]

                    # Combine DICOM Slices to a single 3D image (voxel)
                    try:
                        voxel_ndarray, ijk_to_xyz = dicom_np.combine_slices(dicomDataset)
                        voxel_ndarray = voxel_ndarray.astype(float)
                        voxel_ndarray = np.swapaxes(voxel_ndarray, 0, 1)
                    except dicom_np.DicomImportException as e:
                        #invalid DICOM data
                        raise

                    # normalization of DICOM voxel
                    rangeNorm = [0,1]
                    norm_voxel_ndarray = (voxel_ndarray-np.min(voxel_ndarray))*(rangeNorm[1]-rangeNorm[0])/(np.max(voxel_ndarray)-np.min(voxel_ndarray))

                    # 2D or 3D patching?
                    if self.patchingMode == DeepLearningArtApp.PATCHING_2D:
                        # 2D patching
                        # mask labeling or path labeling
                        if self.labelingMode == DeepLearningArtApp.MASK_LABELING:
                            # path to marking file
                            currentMarkingsPath = self.getMarkingsPath() + os.sep + patient + ".json"
                            # get the markings mask
                            labelMask_ndarray = create_MASK_Array(currentMarkingsPath, patient, dataset, voxel_ndarray.shape[0],
                                                                  voxel_ndarray.shape[1], voxel_ndarray.shape[2])

                            #compute 2D Mask labling patching
                            dPatches, dLabels = fRigidPatching_maskLabeling(norm_voxel_ndarray,
                                                                            [self.patchSizeX, self.patchSizeY],
                                                                            self.patchOverlapp,
                                                                            labelMask_ndarray, 0.5,
                                                                            DeepLearningArtApp.datasets[dataset])

                            # convert to float32
                            dPatches = np.asarray(dPatches, dtype=np.float32)
                            dLabels = np.asarray(dLabels, dtype=np.float32)


                            ############################################################################################
                            if self.usingSegmentationMasks:
                                dPatchesOfMask, dLabelsMask = fRigidPatching_maskLabeling(labelMask_ndarray,
                                                                                [self.patchSizeX, self.patchSizeY],
                                                                                self.patchOverlapp,
                                                                                labelMask_ndarray, 0.5,
                                                                                DeepLearningArtApp.datasets[dataset])

                                dPatchesOfMask = np.asarray(dPatchesOfMask, dtype=np.byte)

                            # sio.savemat('D:med_data/' + patient + '_' + dataset + '_voxel_and_mask.mat',
                            #             {'mask': labelMask_ndarray, 'voxel': voxel_ndarray,
                            #              'dicomPatches': dPatches, 'dicomLabels': dLabels, 'maskPatches': dPatchesOfMask,
                            #              'maskLabels': dLabelsMask})
                            ############################################################################################


                        elif self.labelingMode == DeepLearningArtApp.PATCH_LABELING:
                            # get label
                            datasetLabel = DeepLearningArtApp.datasets[dataset].getDatasetLabel()

                            #compute 2D patch labeling patching
                            dPatches, dLabels = fRigidPatching_patchLabeling(norm_voxel_ndarray,
                                                                             [self.patchSizeX, self.patchSizeY],
                                                                             self.patchOverlapp, 1)
                            dLabels = dLabels*datasetLabel

                            # convert to float32
                            dPatches = np.asarray(dPatches, dtype=np.float32)
                            dLabels = np.asarray(dLabels, dtype=np.float32)
                    elif self.patchingMode == DeepLearningArtApp.PATCHING_3D:
                        # 3D Patching
                        if self.labelingMode == DeepLearningArtApp.MASK_LABELING:
                            # path to marking file
                            currentMarkingsPath = self.getMarkingsPath() + os.sep + patient + ".json"
                            # get the markings mask
                            labelMask_ndarray = create_MASK_Array(currentMarkingsPath, patient, dataset,
                                                                  voxel_ndarray.shape[0],
                                                                  voxel_ndarray.shape[1], voxel_ndarray.shape[2])

                            # compute 3D Mask labling patching
                            dPatches, dLabels = fRigidPatching3D_maskLabeling(norm_voxel_ndarray,
                                                                 [self.patchSizeX, self.patchSizeY, self.patchSizeZ],
                                                                 self.patchOverlapp,
                                                                 labelMask_ndarray,
                                                                 0.5,
                                                                 DeepLearningArtApp.datasets[dataset])

                            # convert to float32
                            dPatches = np.asarray(dPatches, dtype=np.float32)
                            dLabels = np.asarray(dLabels, dtype=np.float32)

                            ############################################################################################
                            if self.usingSegmentationMasks:
                                dPatchesOfMask, dLabelsMask = fRigidPatching3D_maskLabeling(labelMask_ndarray,
                                                                                          [self.patchSizeX, self.patchSizeY, self.patchSizeZ],
                                                                                          self.patchOverlapp,
                                                                                          labelMask_ndarray, 0.5,
                                                                                          DeepLearningArtApp.datasets[dataset])
                                dPatchesOfMask = np.asarray(dPatchesOfMask, dtype=np.byte)
                            ############################################################################################

                        elif self.labelingMode == DeepLearningArtApp.PATCH_LABELING:
                            print("3D local patch labeling not available until now!")

                    else:
                            print("We do not know what labeling mode you want to use :p")

                if self.storeMode == DeepLearningArtApp.STORE_PATCH_BASED:
                    # patch based storage
                    if self.patchingMode == DeepLearningArtApp.PATCHING_3D:
                        for i in range(0, dPatches.shape[3]):
                            patchSlice = np.asarray(dPatches[:,:,:,i], dtype=np.float32)
                            np.save((outPutFolderDataPath + os.sep + "X"+str(iPatchToDisk)+".npy"), patchSlice, allow_pickle=False)
                            labelDict["Y"+str(iPatchToDisk)] = int(dLabels[i])
                            iPatchToDisk+=1
                    else:
                        for i in range(0, dPatches.shape[2]):
                            patchSlice = np.asarray(dPatches[:,:,i], dtype=np.float32)
                            np.save((outPutFolderDataPath + os.sep + "X"+str(iPatchToDisk)+".npy"), patchSlice, allow_pickle=False)
                            labelDict["Y"+str(iPatchToDisk)] = int(dLabels[i])
                            iPatchToDisk+=1

                else:
                    # concatenate all patches in one array
                    if self.patchingMode == DeepLearningArtApp.PATCHING_2D:
                        dAllPatches = np.concatenate((dAllPatches, dPatches), axis=2)
                        dAllLabels = np.concatenate((dAllLabels, dLabels), axis=0)
                        if self.usingSegmentationMasks:
                            dAllSegmentationMaskPatches = np.concatenate((dAllSegmentationMaskPatches, dPatchesOfMask), axis=2)
                    elif self.patchingMode == DeepLearningArtApp.PATCHING_3D:
                        dAllPatches = np.concatenate((dAllPatches, dPatches), axis=3)
                        dAllLabels = np.concatenate((dAllLabels, dLabels), axis=0)
                        if self.usingSegmentationMasks:
                            dAllSegmentationMaskPatches = np.concatenate((dAllSegmentationMaskPatches, dPatchesOfMask), axis=3)


        # dataset splitting
        # store mode
        if self.storeMode != DeepLearningArtApp.STORE_DISABLED:
            # H5py store mode
            if self.storeMode == DeepLearningArtApp.STORE_HDF5:
                # train, validation, test datasets are computed by splitting all data
                if self.patchingMode == DeepLearningArtApp.PATCHING_2D:
                    if not self.usingSegmentationMasks:
                        [self.X_train], [self.Y_train], [self.X_validation], [self.Y_validation], [self.X_test], [self.Y_test] \
                            = fSplitDataset(dAllPatches, dAllLabels, allPats=self.selectedPatients,
                                            sSplitting=self.splittingMode,
                                            patchSize=[self.patchSizeX, self.patchSizeY],
                                            patchOverlap=self.patchOverlapp,
                                            testTrainingDatasetRatio=self.trainTestDatasetRatio,
                                            validationTrainRatio=self.trainValidationRatio,
                                            outPutPath=self.pathOutputPatching, nfolds=0)
                    else:
                        # do segmentation mask split
                        [self.X_train], [self.Y_train], [self.Y_segMasks_train], \
                        [self.X_validation], [self.Y_validation], [self.Y_segMasks_validation], \
                        [self.X_test], [self.Y_test], [self.Y_segMasks_test] \
                            = fSplitSegmentationDataset(dAllPatches, dAllLabels, dAllSegmentationMaskPatches,
                                                        allPats=self.selectedPatients,
                                                        sSplitting=self.splittingMode,
                                                        patchSize=[self.patchSizeX, self.patchSizeY],
                                                        patchOverlap=self.patchOverlapp,
                                                        testTrainingDatasetRatio=self.trainTestDatasetRatio,
                                                        validationTrainRatio=self.trainValidationRatio,
                                                        outPutPath=self.pathOutputPatching, nfolds=0)

                    # store datasets with h5py
                    with h5py.File(outputFolderPath + os.sep + 'datasets.hdf5', 'w') as hf:
                        hf.create_dataset('X_train', data=self.X_train)
                        hf.create_dataset('X_validation', data=self.X_validation)
                        hf.create_dataset('X_test', data=self.X_test)
                        hf.create_dataset('Y_train', data=self.Y_train)
                        hf.create_dataset('Y_validation', data=self.Y_validation)
                        hf.create_dataset('Y_test', data=self.Y_test)
                        if self.usingSegmentationMasks == True:
                            hf.create_dataset('Y_segMasks_train', data=self.Y_segMasks_train)
                            hf.create_dataset('Y_segMasks_validation', data=self.Y_segMasks_validation)
                            hf.create_dataset('Y_segMasks_test', data=self.Y_segMasks_test)

                elif self.patchingMode == DeepLearningArtApp.PATCHING_3D:
                    if not self.usingSegmentationMasks:
                        [self.X_train], [self.Y_train], [self.X_validation], [self.Y_validation], [self.X_test], [
                            self.Y_test] \
                            = fSplitDataset(dAllPatches, dAllLabels, allPats=self.selectedPatients,
                                            sSplitting=self.splittingMode,
                                            patchSize=[self.patchSizeX, self.patchSizeY, self.patchSizeZ],
                                            patchOverlap=self.patchOverlapp,
                                            testTrainingDatasetRatio=self.trainTestDatasetRatio,
                                            validationTrainRatio=self.trainValidationRatio,
                                            outPutPath=self.pathOutputPatching, nfolds=0)
                    else:
                        [self.X_train], [self.Y_train], [self.Y_segMasks_train], \
                        [self.X_validation], [self.Y_validation], [self.Y_segMasks_validation], \
                        [self.X_test], [self.Y_test], [self.Y_segMasks_test]\
                            = fSplitSegmentationDataset(dAllPatches,
                                                        dAllLabels,
                                                        dAllSegmentationMaskPatches,
                                                        allPats=self.selectedPatients,
                                                        sSplitting=self.splittingMode,
                                                        patchSize=[self.patchSizeX, self.patchSizeY, self.patchSizeZ],
                                                        patchOverlap=self.patchOverlapp,
                                                        testTrainingDatasetRatio=self.trainTestDatasetRatio,
                                                        validationTrainRatio=self.trainValidationRatio,
                                                        outPutPath=self.pathOutputPatching,
                                                        nfolds=0)

                    # store datasets with h5py
                    with h5py.File(outputFolderPath+os.sep+'datasets.hdf5', 'w') as hf:
                        hf.create_dataset('X_train', data=self.X_train)
                        hf.create_dataset('X_validation', data=self.X_validation)
                        hf.create_dataset('X_test', data=self.X_test)
                        hf.create_dataset('Y_train', data=self.Y_train)
                        hf.create_dataset('Y_validation', data=self.Y_validation)
                        hf.create_dataset('Y_test', data=self.Y_test)
                        if self.usingSegmentationMasks:
                            hf.create_dataset('Y_segMasks_train', data=self.Y_segMasks_train)
                            hf.create_dataset('Y_segMasks_validation', data=self.Y_segMasks_validation)
                            hf.create_dataset('Y_segMasks_test', data=self.Y_segMasks_test)

            elif self.storeMode == DeepLearningArtApp.STORE_PATCH_BASED:
                with open(outputFolderPath+os.sep+"labels.json", 'w') as fp:
                    json.dump(labelDict, fp)
        else:
            # no storage of patched datasets
            if self.patchingMode == DeepLearningArtApp.PATCHING_2D:
                if not self.usingSegmentationMasks:
                    [self.X_train], [self.Y_train], [self.X_validation], [self.Y_validation], [self.X_test], [
                        self.Y_test] \
                        = fSplitDataset(dAllPatches, dAllLabels, allPats=self.selectedPatients,
                                        sSplitting=self.splittingMode,
                                        patchSize=[self.patchSizeX, self.patchSizeY],
                                        patchOverlap=self.patchOverlapp,
                                        testTrainingDatasetRatio=self.trainTestDatasetRatio,
                                        validationTrainRatio=self.trainValidationRatio,
                                        outPutPath=self.pathOutputPatching, nfolds=0)
                else:
                    # do segmentation mask split
                    [self.X_train], [self.Y_train], [self.Y_segMasks_train], \
                    [self.X_validation], [self.Y_validation], [self.Y_segMasks_validation], \
                    [self.X_test], [self.Y_test], [self.Y_segMasks_test] \
                        = fSplitSegmentationDataset(dAllPatches,
                                                    dAllLabels,
                                                    dAllSegmentationMaskPatches,
                                                    allPats=self.selectedPatients,
                                                    sSplitting=self.splittingMode,
                                                    patchSize=[self.patchSizeX, self.patchSizeY],
                                                    patchOverlap=self.patchOverlapp,
                                                    testTrainingDatasetRatio=self.trainTestDatasetRatio,
                                                    validationTrainRatio=self.trainValidationRatio,
                                                    outPutPath=self.pathOutputPatching,
                                                    nfolds=0)

            elif self.patchingMode == DeepLearningArtApp.PATCHING_3D:
                if not self.usingSegmentationMasks:
                    [self.X_train], [self.Y_train], [self.X_validation], [self.Y_validation], [self.X_test], [
                        self.Y_test] \
                        = fSplitDataset(dAllPatches, dAllLabels, allPats=self.selectedPatients,
                                        sSplitting=self.splittingMode,
                                        patchSize=[self.patchSizeX, self.patchSizeY, self.patchSizeZ],
                                        patchOverlap=self.patchOverlapp,
                                        testTrainingDatasetRatio=self.trainTestDatasetRatio,
                                        validationTrainRatio=self.trainValidationRatio,
                                        outPutPath=self.pathOutputPatching, nfolds=0)
                else:
                    [self.X_train], [self.Y_train], [self.Y_segMasks_train], \
                    [self.X_validation], [self.Y_validation], [self.Y_segMasks_validation], \
                    [self.X_test], [self.Y_test], [self.Y_segMasks_test] \
                        = fSplitSegmentationDataset(dAllPatches,
                                                    dAllLabels,
                                                    dAllSegmentationMaskPatches,
                                                    allPats=self.selectedPatients,
                                                    sSplitting=self.splittingMode,
                                                    patchSize=[self.patchSizeX, self.patchSizeY, self.patchSizeZ],
                                                    patchOverlap=self.patchOverlapp,
                                                    testTrainingDatasetRatio=self.trainTestDatasetRatio,
                                                    validationTrainRatio=self.trainValidationRatio,
                                                    outPutPath=self.pathOutputPatching,
                                                    nfolds=0)

            print()

    def performTraining(self):
        # get output vector for different classes
        classes = np.asarray(np.unique(self.Y_train, ), dtype=int)
        classMappings = Label.mapClassesToOutputVector(classes=classes,
                                                       usingArtefacts=self.usingArtifacts,
                                                       usingBodyRegion=self.usingBodyRegions,
                                                       usingTWeightings=self.usingTWeighting)

        Y_train = []
        for i in range(self.Y_train.shape[0]):
            Y_train.append(classMappings[self.Y_train[i]])
        Y_train = np.asarray(Y_train)

        Y_validation = []
        for i in range(self.Y_validation.shape[0]):
            Y_validation.append(classMappings[self.Y_validation[i]])
        Y_validation = np.asarray(Y_validation)

        Y_test = []
        for i in range(self.Y_test.shape[0]):
            Y_test.append(classMappings[self.Y_test[i]])
        Y_test = np.asarray(Y_test)

        # output folder
        outPutFolderDataPath = self.learningOutputPath + os.sep + self.neuralNetworkModel + "_"
        if self.patchingMode == DeepLearningArtApp.PATCHING_2D:
            outPutFolderDataPath += "2D" + "_" + str(self.patchSizeX) + "x" + str(self.patchSizeY)
        elif self.patchingMode == DeepLearningArtApp.PATCHING_3D:
            outPutFolderDataPath += "3D" + "_" + str(self.patchSizeX) + "x" + str(self.patchSizeY) + \
                                    "x" + str(self.patchSizeZ)

        outPutFolderDataPath += "_" + datetime.datetime.today().strftime('%Y-%m-%d_%H-%M')

        if not os.path.exists(outPutFolderDataPath):
            os.makedirs(outPutFolderDataPath)

        if not os.path.exists(outPutFolderDataPath + os.sep + 'checkpoints'):
            os.makedirs(outPutFolderDataPath + os.sep + 'checkpoints')

        # summarize cnn and training
        self.create_cnn_training_summary(self.neuralNetworkModel, outPutFolderDataPath)

        if self.Y_segMasks_test is not None and self.Y_segMasks_train is not None and self.Y_segMasks_validation is not None:
            self.usingSegmentationMasks = True
        else:
            self.usingSegmentationMasks = False

        if not self.usingSegmentationMasks:
            cnn_main.fRunCNN(dData={'X_train': self.X_train, 'y_train': Y_train, 'X_valid': self.X_validation, 'y_valid': Y_validation ,
                                    'X_test': self.X_test, 'y_test': Y_test, 'patchSize': [self.patchSizeX, self.patchSizeY, self.patchSizeZ]},
                             sModelIn=DeepLearningArtApp.deepNeuralNetworks[self.neuralNetworkModel],
                             lTrain=cnn_main.RUN_CNN_TRAIN_TEST_VALIDATION,
                             sParaOptim='',
                             sOutPath=outPutFolderDataPath,
                             iBatchSize=self.batchSizes,
                             iLearningRate=self.learningRates,
                             iEpochs=self.epochs,
                             dlart_handle=self)
        else:
            # segmentation FCN training
            cnn_main.fRunCNN(dData={'X_train': self.X_train,
                                    'y_train': Y_train,
                                    'Y_segMasks_train': self.Y_segMasks_train,
                                    'X_valid': self.X_validation,
                                    'y_valid': Y_validation,
                                    'Y_segMasks_validation': self.Y_segMasks_validation,
                                    'X_test': self.X_test,
                                    'y_test': Y_test,
                                    'Y_segMasks_test': self.Y_segMasks_test,
                                    'patchSize': [self.patchSizeX, self.patchSizeY, self.patchSizeZ]},
                             sModelIn=DeepLearningArtApp.deepNeuralNetworks[self.neuralNetworkModel],
                             lTrain=cnn_main.RUN_CNN_TRAIN_TEST_VALIDATION,
                             sParaOptim='',
                             sOutPath=outPutFolderDataPath,
                             iBatchSize=self.batchSizes,
                             iLearningRate=self.learningRates,
                             iEpochs=self.epochs,
                             dlart_handle=self,
                             usingSegmentationMasks=self.usingSegmentationMasks)


    def getAllDicomsPathList(self):
        '''

        :return: a list with all paths of dicoms from the selected patients and selected datasets
        '''
        allDicomsPathList = []
        for patient in self.selectedPatients:
            for dataset in self.selectedDatasets:
                curDataDir = self.pathDatabase + os.sep + patient + os.sep + self.modelSubDir + os.sep + dataset
                if os.path.exists(curDataDir):  # check if path exists... especially for the dicom_sorted subdir!!!!!
                    fileNames = tf.gfile.ListDirectory(curDataDir)
                    fileNames = [os.path.join(curDataDir, f) for f in fileNames]
                    allDicomsPathList = allDicomsPathList + fileNames
        return allDicomsPathList

    def create_cnn_training_summary(self, name, outputFolderPath):
        dataDict = {}
        dataDict['Name'] = name
        dataDict['Date'] = datetime.datetime.today().strftime('%Y-%m-%d')
        dataDict['BatchSize'] = ''.join(str(e) for e in self.batchSizes)
        dataDict['LearningRate'] = ''.join(str(e) for e in self.batchSizes)
        dataDict['DataAugmentation'] = self.dataAugmentationEnabled
        dataDict['HorizontalFlip'] = self.horizontalFlip
        dataDict['VerticalFlip'] = self.verticalFlip
        dataDict['Rotation'] = self.rotation
        dataDict['Zoom'] = self.zoom
        dataDict['ZCA_Whitening'] = self.zcaWhitening
        dataDict['HeightShift'] = self.heightShift
        dataDict['WidthShift'] = self.widthShift
        dataDict['ContrastStretching'] = self.contrastStretching
        dataDict['HistogramEq'] = self.histogram_eq
        dataDict['AdaptiveEq'] = self.adaptive_eq

        dataDict['BodyRegions'] = self.usingBodyRegions
        dataDict['TWeightings'] = self.usingTWeighting
        dataDict['Artifacts'] = self.usingArtifacts

        dataDict['Optimizer'] = self.optimizer
        dataDict['Epochs'] = self.epochs
        dataDict['WeightDecay'] = self.weightDecay
        dataDict['Momentum'] = self.momentum
        dataDict['NesterovEnabled'] = self.nesterovEnabled

        dataDict['Dataset'] = self.datasetName

        with open((outputFolderPath+os.sep+'cnn_training_info.json'), 'w') as fp:
            json.dump(dataDict, fp, indent=4)



    def createDatasetInfoSummary(self, name, outputFolderPath):
        '''
        creates a json info summary of the patched dataset
        :param outputFolderPath:
        :return:
        '''
        dataDict = {}
        dataDict['Name'] = name
        dataDict['Date'] = datetime.datetime.today().strftime('%Y-%m-%d')
        dataDict['Patients'] = self.selectedPatients
        dataDict['Datasets'] = self.selectedDatasets
        dataDict['PatchMode'] = self.patchingMode
        dataDict['PatchSizeX'] = self.patchSizeX
        dataDict['PatchSizeY'] = self.patchSizeY
        dataDict['PatchSizeZ'] = self.patchSizeZ
        dataDict['PatchOverlap'] = self.patchOverlapp
        dataDict['LabelingMode'] = self.labelingMode
        dataDict['SplittingMode'] = self.splittingMode
        dataDict['NumFolds'] = self.numFolds
        dataDict['TrainTestRatio'] = self.trainTestDatasetRatio
        dataDict['TrainValidationRatio'] = self.trainValidationRatio
        dataDict['StoreMode'] = self.storeMode
        dataDict['SegmentationMaskUsed'] = self.usingSegmentationMasks

        with open((outputFolderPath+os.sep+'dataset_info.json'), 'w') as fp:
            json.dump(dataDict, fp, indent=4)

    def setLabelingMode(self, mode):
        if mode == DeepLearningArtApp.MASK_LABELING or mode == DeepLearningArtApp.PATCH_LABELING:
            self.labelingMode = mode

    def getLabelingMode(self):
        return self.labelingMode

    def setMarkingsPath(self, path):
        self.markingsPath = path

    def getMarkingsPath(self):
        return self.markingsPath

    def setPatchSizeX(self, s):
        self.patchSizeX = s

    def getPatchSizeX(self):
        return self.patchSizeX

    def setPatchSizeY(self, s):
        self.patchSizeY = s

    def getPatchSizeY(self):
        return self.patchSizeY

    def setPatchSizeZ(self, s):
        self.patchSizeZ = s

    def getPatchSizeZ(self):
        return self.patchSizeZ

    def setPatchOverlapp(self, o):
        self.patchOverlapp = o

    def getPatchOverlapp(self):
        return self.patchOverlapp

    def setPathToDatabase(self, pathToDB):
        self.pathDatabase = pathToDB

    def getPathToDatabase(self):
        return self.pathDatabase

    def setOutputPathForPatching(self, outPath):
        self.pathOutputPatching = outPath

    def getOutputPathForPatching(self):
        return self.pathOutputPatching

    def setSelectedPatients(self, pats):
        self.selectedPatients = pats

    def getSelectedPatients(self):
        return self.selectedPatients

    def setSelectedDatasets(self, sets):
        self.selectedDatasets = sets

    def getSelectedDatasets(self):
        return self.selectedDatasets

    def setPatchingMode(self, mode):
        if mode == DeepLearningArtApp.PATCHING_2D or mode == DeepLearningArtApp.PATCHING_3D:
            self.patchingMode = mode

    def getPatchingMode(self):
        return self.patchingMode

    def getLearningOutputPath(self):
        return self.learningOutputPath

    def setLearningOutputPath(self, path):
        self.learningOutputPath = path

    def getStoreMode(self):
        return self.storeMode

    def setStoreMode(self, mode):
        if mode == 0:
            self.storeMode = DeepLearningArtApp.STORE_DISABLED
        elif mode == 1:
            self.storeMode = DeepLearningArtApp.STORE_HDF5
        elif mode == 2:
            self.storeMode = DeepLearningArtApp.STORE_PATCH_BASED
        else:
            raise ValueError('Unknown store mode!!!')

    def getTrainTestDatasetRatio(self):
        '''
        Function returns the splitting ratio of dataset into training set and test set
        :return: splitting ratio
        '''
        return self.trainTestDatasetRatio

    def setTrainTestDatasetRatio(self, ratio):
        if 0 < ratio < 1:
            self.trainTestDatasetRatio = ratio
        else:
            raise ValueError('Splitting ratio train set, test set too big or too small!')

    def getTrainValidationRatio(self):
        '''
        Function returns the splitting ratio of training set into sets used for training and validation
        :return:
        '''
        return self.trainValidationRatio

    def setTrainValidationRatio(self, ratio):
        if 0 <= ratio < 1:
            self.trainValidationRatio = ratio
        else:
            raise ValueError('Splitting ratio train, validation on training set is too big or too small!')

    def setSplittingMode(self, mode):
        self.splittingMode = mode

    def getSplittingMode(self):
        return self.splittingMode

    def getNumFolds(self):
        return self.numFolds

    def setNumFolds(self, folds):
        self.numFolds = folds

    def setNeuralNetworkModel(self, model):
        self.neuralNetworkModel = model

    def getNeuralNetworkModel(self):
        return self.neuralNetworkModel

    def setBatchSizes(self, size):
        self.batchSizes = size

    def getBatchSizes(self):
        return self.batchSizes

    def setLearningRates(self, rates):
        self.learningRates = rates

    def getLearningRates(self):
        return self.learningRates

    def setEpochs(self, epochs):
        self.epochs = epochs

    def getEpochs(self):
        return self.epochs

    def getUsingArtifacts(self):
        return self.usingArtifacts

    def setUsingArtifacts(self, b):
        self.usingArtifacts = b

    def getUsingBodyRegions(self):
        return self.usingBodyRegions

    def setUsingBodyRegions(self, b):
        self.usingBodyRegions = b

    def getUsingTWeighting(self):
        return self.usingBodyRegions

    def setUsingTWeighting(self, b):
        self.usingTWeighting = b

    def setOptimizer(self, opt):
        self.optimizer = opt

    def getOptimizer(self):
        return self.optimizer

    def setWeightDecay(self, w):
        self.weightDecay = w

    def getWeightDecay(self):
        return self.weightDecay

    def setMomentum(self, m):
        self.momentum = m

    def getMomentum(self):
        return self.momentum

    def setNesterovEnabled(self, n):
        self.nesterovEnabled = n

    def getNesterovEnabled(self):
        return self.nesterovEnabled

    def setDataAugmentationEnabled(self, b):
        self.dataAugmentationEnabled = b

    def getDataAugmentationEnabled(self):
        return self.dataAugmentationEnabled

    def setHorizontalFlip(self, b):
        self.horizontalFlip = b

    def getHorizontalFlip(self):
        return self.horizontalFlip

    def setVerticalFlip(self, b):
        self.verticalFlip = b

    def getVerticalFlip(self):
        return self.verticalFlip

    def setRotation(self, b):
        if b:
            self.rotation = DeepLearningArtApp.ROTATION_RANGE
        else:
            self.rotation = 0

    def getRotation(self):
        return self.rotation

    def setZCA_Whitening(self, b):
        self.zcaWhitening = b

    def getZCA_Whitening(self):
        return self.zcaWhitening

    def setHeightShift(self, b):
        if b:
            self.heightShift = DeepLearningArtApp.HEIGHT_SHIFT_RANGE
        else:
            self.heightShift = 0

    def getHeightShift(self):
        return self.heightShift

    def setWidthShift(self, b):
        if b:
            self.widthShift = DeepLearningArtApp.WIDTH_SHIFT_RANGE
        else:
            self.widthShift = 0

    def getWidthShift(self):
        return self.widthShift

    def setZoom(self, r):
        if r:
            self.zoom = DeepLearningArtApp.ZOOM_RANGE
        else:
            self.zoom = 0

    def getZoom(self):
        return self.zoom

    def setContrastStretching(self, c):
        self.contrastStretching = c

    def getContrastStretching(self):
        return self.contrastStretching

    def setAdaptiveEqualization(self, e):
        self.adaptive_eq = e

    def getAdaptiveEqualization(self):
        return self.adaptive_eq

    def setHistogramEqualization(self, e):
        self.histogram_eq = e

    def getHistogramEqualization(self):
        return self.histogram_eq

    def setGUIHandle(self, handle):
        self.dlart_GUI_handle = handle

    def getGUIHandle(self):
        return self.dlart_GUI_handle

    def getUsingSegmentationMasks(self):
        return self.usingSegmentationMasks

    def setUsingSegmentationMasks(self, b):
        self.usingSegmentationMasks = b

    def datasetAvailable(self):
        retbool = False
        if self.storeMode != DeepLearningArtApp.STORE_PATCH_BASED:
            if self.X_train is not None and self.X_validation is not None \
                    and self.X_test is not None and self.Y_train is not None \
                    and self.Y_validation is not None and self.Y_test.all is not None:
                retbool = True
        return retbool

    def updateProgressBarTraining(self, val):
        self.dlart_GUI_handle.updateProgressBarTraining(val)

    def loadDataset(self, pathToDataset):
        '''
        Method loads an existing dataset out of hd5f files or handles the patch based datasets
        :param pathToDataset: path to dataset
        :return: boolean if loading was successful, and name of loaded dataset
        '''
        retbool = False
        #check for data info summary in json file
        try:
            with open(pathToDataset + os.sep + "dataset_info.json", 'r') as fp:
                dataset_info = json.load(fp)

            # hd5f or patch based?
            if dataset_info['StoreMode'] == DeepLearningArtApp.STORE_HDF5:
                # loading hdf5
                self.datasetName = dataset_info['Name']
                self.patchSizeX = int(dataset_info['PatchSizeX'])
                self.patchSizeY = int(dataset_info['PatchSizeY'])
                self.patchSizeZ = int(dataset_info['PatchSizeZ'])
                self.patchOverlapp = float(dataset_info['PatchOverlap'])
                self.patchingMode = int(dataset_info['PatchMode'])
                self.labelingMode = int(dataset_info['LabelingMode'])
                self.splittingMode = int(dataset_info['SplittingMode'])
                self.trainTestDatasetRatio = float(dataset_info['TrainTestRatio'])
                self.trainValidationRatio = float(dataset_info['TrainValidationRatio'])
                self.numFolds = int(dataset_info['NumFolds'])
                try:
                    self.usingSegmentationMasks = bool(dataset_info['SegmentationMaskUsed'])
                except:
                    self.usingSegmentationMasks = False

                # loading hdf5 dataset
                try:
                    with h5py.File(pathToDataset + os.sep + "datasets.hdf5", 'r') as hf:
                        self.X_train = hf['X_train'][:]
                        self.X_validation = hf['X_validation'][:]
                        self.X_test = hf['X_test'][:]
                        self.Y_train = hf['Y_train'][:]
                        self.Y_validation = hf['Y_validation'][:]
                        self.Y_test = hf['Y_test'][:]
                        if self.usingSegmentationMasks:
                            self.Y_segMasks_train = hf['Y_segMasks_train'][:]
                            self.Y_segMasks_validation = hf['Y_segMasks_validation'][:]
                            self.Y_segMasks_test = hf['Y_segMasks_test'][:]

                    retbool = True
                except:
                    raise TypeError("Can't read HDF5 dataset!")

            elif dataset_info['StoreMode'] == DeepLearningArtApp.STORE_PATCH_BASED:
                #loading patchbased stuff
                self.datasetName = dataset_info['Name']

                print("still in progrss")
            else:
                raise NameError("No such store Mode known!")

        except:
            raise FileNotFoundError("Error: Something went wrong at trying to load the dataset!!!")

        return retbool, self.datasetName



    ####################################################################################################################
    ####  ArtGAN Stuff
    ####################################################################################################################

    def generateDataset_ArtGAN(self):

        self.Art_test = []
        self.Art_train = []
        self.Ref_test = []
        self.Ref_train = []

        if self.patchingMode == DeepLearningArtApp.PATCHING_2D:
            dAllPatches_art = np.zeros((self.patchSizeX_ArtGAN, self.patchSizeY_ArtGAN, 0))
            dAllPatches_ref = np.zeros((self.patchSizeX_ArtGAN, self.patchSizeY_ArtGAN, 0))
        elif self.patchingMode == DeepLearningArtApp.PATCHING_3D:
            dAllPatches_art = np.zeros([self.patchSizeX_ArtGAN, self.patchSizeY_ArtGAN, self.patchSizeZ_ArtGAN, 0])
            dAllPatches_ref = np.zeros([self.patchSizeX_ArtGAN, self.patchSizeY_ArtGAN, self.patchSizeZ_ArtGAN, 0])
        else:
            raise IOError("What's your plan, man? We do not know your patching mode...")

        # stuff for storing
        if self.storeMode_ArtGAN != DeepLearningArtApp.STORE_DISABLED:
            # outPutFolder name:
            outPutFolder = "ArtGAN_" + str(len(self.patients_ArtGAN)) + "Patients_P" + \
                str(self.patchSizeX_ArtGAN) + "x" + str(self.patchSizeY_ArtGAN) + "_O" + str(self.patchOverlap_ArtGAN)

            outputFolderPath = self.pathOutputPatchingGAN + os.sep + outPutFolder

            if not os.path.exists(outputFolderPath):
                os.makedirs(outputFolderPath)

            # create dataset summary
            self.createDatasetInfoSummary_ArtGAN(outPutFolder, outputFolderPath)

            if self.storeMode_ArtGAN == DeepLearningArtApp.STORE_PATCH_BASED:
                outPutFolderDataPathArts = outputFolderPath + os.sep + "data_arts"
                outPutFolderDataPathRefs = outputFolderPath + os.sep + "data_refs"
                if not os.path.exists(outPutFolderDataPathArts):
                    os.makedirs(outPutFolderDataPathArts)
                if not os.path.exists(outPutFolderDataPathRefs):
                    os.makedirs(outPutFolderDataPathRefs)

                labelDict = {}

        # for storing patch based
        iPatchToDisk = 0

        for patient in self.patients_ArtGAN:
            for dataset in self.datasets_ArtGAN_Pairs.keys():
                # for artefact dataset
                currentArtDataDir = self.pathDatabase + os.sep + patient + os.sep + self.modelSubDir + os.sep + dataset
                # for ref dataset
                currentRefDataDir = self.pathDatabase + os.sep + patient + os.sep + self.modelSubDir +\
                                    os.sep + self.datasets_ArtGAN_Pairs[dataset]

                if os.path.exists(currentArtDataDir) and os.path.exists(currentRefDataDir):
                    # get list with all paths of dicoms for current patient and current dataset
                    fileNamesArt = tf.gfile.ListDirectory(currentArtDataDir)
                    fileNamesRef = tf.gfile.ListDirectory(currentRefDataDir)

                    fileNamesArt = [os.path.join(currentArtDataDir, f) for f in fileNamesArt]
                    fileNamesRef = [os.path.join(currentRefDataDir, f) for f in fileNamesRef]

                    # read DICOMS
                    dicomDatasetArt = [dicom.read_file(f) for f in fileNamesArt]
                    dicomDatasetRef = [dicom.read_file(f) for f in fileNamesRef]

                    # Combine DICOM Slices to a single 3D image (voxel)
                    try:
                        voxel_ndarray_art, ijk_to_xyz_art = dicom_np.combine_slices(dicomDatasetArt)
                        voxel_ndarray_art = voxel_ndarray_art.astype(float)
                        voxel_ndarray_art = np.swapaxes(voxel_ndarray_art, 0, 1)
                        voxel_ndarray_ref, ijk_to_xyz_ref = dicom_np.combine_slices(dicomDatasetRef)
                        voxel_ndarray_ref = voxel_ndarray_ref.astype(float)
                        voxel_ndarray_ref = np.swapaxes(voxel_ndarray_ref, 0, 1)
                    except dicom_np.DicomImportException as e:
                        # invalid DICOM data
                        raise

                    # normalization of DICOM voxels
                    rangeNorm = [0, 1]
                    norm_voxel_ndarray_art = (voxel_ndarray_art - np.min(voxel_ndarray_art)) \
                                             * (rangeNorm[1] - rangeNorm[0]) \
                                             / (np.max(voxel_ndarray_art) - np.min(voxel_ndarray_art))
                    norm_voxel_ndarray_ref = (voxel_ndarray_ref - np.min(voxel_ndarray_ref)) \
                                             * (rangeNorm[1] - rangeNorm[0]) \
                                             / (np.max(voxel_ndarray_ref) - np.min(voxel_ndarray_ref))

                    # 2D patching
                    #datasetLabel_art = DeepLearningArtApp.datasets[dataset].getDatasetLabel()
                    #datasetLabel_ref = DeepLearningArtApp.datasets[self.datasets_ArtGAN_Pairs[dataset]].getDatasetLabel()

                    # compute 2D patch labeling patching
                    dPatches_art, dLabels_art = fRigidPatching_patchLabeling(norm_voxel_ndarray_art,
                                                                             [self.patchSizeX_ArtGAN, self.patchSizeY_ArtGAN],
                                                                             self.patchOverlap_ArtGAN,
                                                                             ratio_labeling=1)
                    dPatches_ref, dLabels_ref = fRigidPatching_patchLabeling(norm_voxel_ndarray_ref,
                                                                             [self.patchSizeX_ArtGAN, self.patchSizeY_ArtGAN],
                                                                             self.patchOverlap_ArtGAN,
                                                                             ratio_labeling=1)

                    #dLabels = dLabels * datasetLabel

                    # convert to float32
                    dPatches_art = np.asarray(dPatches_art, dtype=np.float32)
                    dPatches_ref = np.asarray(dPatches_ref, dtype=np.float32)

                if self.storeMode_ArtGAN == DeepLearningArtApp.STORE_PATCH_BASED:
                    for i in range(0, dPatches_art.shape[2]):
                        # artifact slice
                        patchSlice = np.asarray(dPatches_art[:, :, i], dtype=np.float32)
                        np.save((outPutFolderDataPathArts + os.sep + "Art" + str(iPatchToDisk) + ".npy"), patchSlice,
                                allow_pickle=False)

                        # reference slice
                        patchSlice = np.asarray(dPatches_ref[:, :, i], dtype=np.float32)
                        np.save((outPutFolderDataPathRefs + os.sep + "Ref" + str(iPatchToDisk) + ".npy"), patchSlice,
                                allow_pickle=False)
                        iPatchToDisk += 1

                else:
                    # concatenate all patches in one array
                    dAllPatches_art = np.concatenate((dAllPatches_art, dPatches_art), axis=2)
                    dAllPatches_ref = np.concatenate((dAllPatches_ref, dPatches_ref), axis=2)

        if self.storeMode_ArtGAN != DeepLearningArtApp.STORE_PATCH_BASED:
            # dataset splitting
            [self.Art_train], [self.Ref_train], _, _, [self.Art_test], [self.Ref_test] \
                = fSplitDataset(dAllPatches_art,
                                dAllPatches_ref,
                                allPats=self.patients_ArtGAN,
                                sSplitting=self.splittingMode_ArtGAN,
                                patchSize=[self.patchSizeX_ArtGAN, self.patchSizeY_ArtGAN],
                                patchOverlap=self.patchOverlap_ArtGAN,
                                testTrainingDatasetRatio=self.trainTestDatasetRatio_ArtGAN,
                                validationTrainRatio=self.trainValidationRatio_ArtGAN,
                                outPutPath=self.pathOutputPatchingGAN,
                                nfolds=self.numFolds)

            # H5py store mode
            if self.storeMode_ArtGAN == DeepLearningArtApp.STORE_HDF5:
                # store datasets with h5py
                pathOutput = outputFolderPath + os.sep + "Pats" + str(len(self.patients_ArtGAN)) + '_' + str(self.patchSizeX_ArtGAN) + \
                    'x' + str(self.patchSizeY_ArtGAN) + '_O' + str(self.patchOverlap_ArtGAN) + '.hdf5'

                with h5py.File(pathOutput, 'w') as hf:
                    hf.create_dataset('Art_train', data=self.Art_train)
                    #hf.create_dataset('X_validation', data=self.X_validation)
                    hf.create_dataset('Art_test', data=self.Art_test)
                    hf.create_dataset('Ref_train', data=self.Ref_train)
                    #hf.create_dataset('Y_validation', data=self.Y_validation)
                    hf.create_dataset('Ref_test', data=self.Ref_test)

    def performTraining_ArtGAN(self):
        artGAN.artGAN_main()

    def getOutputPathPatchingGAN(self):
        return self.pathOutputPatchingGAN

    def setOutputPathPatchingGAN(self, path):
        self.pathOutputPatchingGAN = path

    def getPatientsArtGAN(self):
        return self.patients_ArtGAN

    def setPatientsArtGAN(self, d):
        self.patients_ArtGAN = d

    def getDatasetArtGAN(self):
        return self.datasets_ArtGAN

    def setDatasetArtGAN(self, d):
        self.datasets_ArtGAN = d

    def setDatasets_ArtGAN_Pairs(self, pairs):
        self.datasets_ArtGAN_Pairs = pairs

    def getDatasets_ArtGAN_Pairs(self):
        return self.datasets_ArtGAN_Pairs

    def fPreprocessDataCorrection(self, trainingMethod, cfg, patchSize, dbinfo):
        """
        Perform patching to reference and artifact images according to given patch size.
        @param cfg: the configuration file loaded from config/param.yml
        @param dbinfo: database related info
        @return: patches from reference and artifact images and an array which stores the corresponding patient index
        """
        train_ref = []
        test_ref = []
        train_art = []
        test_art = []

        sTrainingMethod = trainingMethod

        scpatchSize = patchSize
        if sTrainingMethod != "scalingPrior":
            lScaleFactor = [1]
        # Else perform scaling:
        #   images will be split into pathces with size scpatchSize and then scaled to patchSize
        for iscalefactor in self.lscaleFactor:
            lDatasets = cfg['selectedDatabase']['dataref'] + cfg['selectedDatabase']['dataart']
            scpatchSize = [int(psi / iscalefactor) for psi in patchSize]
            if len(patchSize) == 3:
                dRefPatches = np.empty((0, scpatchSize[0], scpatchSize[1], scpatchSize[2]))
                dArtPatches = np.empty((0, scpatchSize[0], scpatchSize[1], scpatchSize[2]))
            else:
                dRefPatches = np.empty((0, scpatchSize[0], scpatchSize[1]))
                dArtPatches = np.empty((0, scpatchSize[0], scpatchSize[1]))

            dRefPats = np.empty((0, 1))
            dArtPats = np.empty((0, 1))

            for ipat, pat in enumerate(dbinfo.lPats):
                if os.path.exists(dbinfo.sPathIn + os.sep + pat + os.sep + dbinfo.sSubDirs[1]):
                    for iseq, seq in enumerate(lDatasets):
                        # patches and labels of reference/artifact
                        tmpPatches, tmpLabels = fPreprocessData(
                            os.path.join(dbinfo.sPathIn, pat, dbinfo.sSubDirs[1], seq),
                            patchSize, cfg['patchOverlap'], 1, 'volume')

                        if iseq == 0:
                            dRefPatches = np.concatenate((dRefPatches, tmpPatches), axis=0)
                            dRefPats = np.concatenate(
                                (dRefPats, ipat * np.ones((tmpPatches.shape[0], 1), dtype=np.int)), axis=0)
                        elif iseq == 1:
                            dArtPatches = np.concatenate((dArtPatches, tmpPatches), axis=0)
                            dArtPats = np.concatenate(
                                (dArtPats, ipat * np.ones((tmpPatches.shape[0], 1), dtype=np.int)), axis=0)
                else:
                    pass

        assert (dRefPatches.shape == dArtPatches.shape and dRefPats.shape == dArtPats.shape)

        # perform splitting
        print('Start splitting')
        train_ref_sp, test_ref_sp, train_art_sp, test_art_sp = ttsplit.fSplitDatasetCorrection(cfg['sSplitting'],
                                                                                               dRefPatches, dArtPatches,
                                                                                               dRefPats,
                                                                                               cfg['dSplitval'],
                                                                                               cfg['nFolds'])
        print('Start scaling')
        # perform scaling: sc for scale
        train_ref_sc, test_ref_sc = scaling.fscaling(train_ref_sp, test_ref_sp, scpatchSize, iscalefactor)
        train_art_sc, test_art_sc = scaling.fscaling(train_art_sp, test_art_sp, scpatchSize, iscalefactor)

        if len(train_ref) == 0:
            train_ref = train_ref_sc
            test_ref = test_ref_sc
            train_art = train_art_sc
            test_art = test_art_sc
        else:
            train_ref = np.concatenate((train_ref, train_ref_sc), axis=1)
            test_ref = np.concatenate((test_ref, test_ref_sc), axis=1)
            train_art = np.concatenate((train_art, train_art_sc), axis=1)
            test_art = np.concatenate((test_art, test_art_sc), axis=1)

        return train_ref, test_ref, train_art, test_art

    def setStoreMode_ArtGAN(self, mode):
        if mode == 0:
            self.storeMode_ArtGAN = DeepLearningArtApp.STORE_DISABLED
        elif mode == 1:
            self.storeMode_ArtGAN = DeepLearningArtApp.STORE_HDF5
        elif mode == 2:
            self.storeMode_ArtGAN = DeepLearningArtApp.STORE_PATCH_BASED
        else:
            raise ValueError('Unknown store mode!!!')

    def getStoreMode_ArtGAN(self):
        return self.storeMode_ArtGAN

    def getPatchSizeX_ArtGAN(self):
        return self.patchSizeX_ArtGAN

    def getPatchSizeY_ArtGAN(self):
        return self.patchSizeY_ArtGAN

    def setPatchSizeX_ArtGAN(self, x):
        self.patchSizeX_ArtGAN = x

    def setPatchSizeY_ArtGAN(self, y):
        self.patchSizeY_ArtGAN = y

    def getPatchSizeZ_ArtGAN(self):
        return self.patchSizeZ_ArtGAN

    def setPatchSizeZ_ArtGAN(self, z):
        self.patchSizeZ_ArtGAN = z

    def getPatchOverlap_ArtGAN(self):
        return self.patchOverlap_ArtGAN

    def setPatchOverlap_ArtGAN(self, o):
        self.patchOverlap_ArtGAN = o

    def createDatasetInfoSummary_ArtGAN(self, name, outputFolderPath):
        '''
        creates a json info summary of the patched dataset
        :param outputFolderPath:
        :return:
        '''
        dataDict = {}
        dataDict['Name'] = name
        dataDict['Date'] = datetime.datetime.today().strftime('%Y-%m-%d')
        dataDict['Patients'] = self.patients_ArtGAN
        dataDict['Datasets'] = self.datasets_ArtGAN_Pairs
        dataDict['PatchSizeX'] = self.patchSizeX_ArtGAN
        dataDict['PatchSizeY'] = self.patchSizeY_ArtGAN
        dataDict['PatchOverlap'] = self.patchOverlap_ArtGAN
        dataDict['SplittingMode'] = self.splittingMode_ArtGAN
        dataDict['StoreMode'] = self.storeMode_ArtGAN

        with open((outputFolderPath+os.sep+'dataset_info.json'), 'w') as fp:
            json.dump(dataDict, fp, indent=4)

    def getArtRefPairLength(self):
        return self.Art_train.shape[0]

    def getArtRefPair(self, num):
        art = self.Art_train[num]
        ref = self.Ref_train[num]

        return art, ref

    def loadDatasetArtGAN(self, pathToDataset):
        '''
        Method loads an existing dataset out of hd5f files or handles the patch based datasets
        :param pathToDataset: path to dataset
        :return: boolean if loading was successful, and name of loaded dataset
        '''
        retbool = False
        datasetName = ''
        #check for data info summary in json file
        try:
            with open(pathToDataset + os.sep + "dataset_info.json", 'r') as fp:
                dataset_info = json.load(fp)

            # hd5f or patch based?
            if dataset_info['StoreMode'] == DeepLearningArtApp.STORE_HDF5:
                # loading hdf5
                datasetName = dataset_info['Name']
                self.patchSizeX = int(dataset_info['PatchSizeX'])
                self.patchSizeY = int(dataset_info['PatchSizeY'])
                self.patchSizeZ = int(dataset_info['PatchSizeZ'])
                self.patchOverlapp = float(dataset_info['PatchOverlap'])

                # loading hdf5 dataset
                try:
                    with h5py.File(pathToDataset + os.sep + "datasets.hdf5", 'r') as hf:
                        self.X_train = hf['X_train'][:]
                        self.X_validation = hf['X_validation'][:]
                        self.X_test = hf['X_test'][:]
                        self.Y_train = hf['Y_train'][:]
                        self.Y_validation = hf['Y_validation'][:]
                        self.Y_test = hf['Y_test'][:]

                    retbool = True
                except:
                    raise TypeError("Can't read HDF5 dataset!")

            elif dataset_info['StoreMode'] == DeepLearningArtApp.STORE_PATCH_BASED:
                #loading patchbased stuff
                datasetName = dataset_info['Name']

                print("still in progrss")
            else:
                raise NameError("No such store Mode known!")

        except:
            raise FileNotFoundError("Error: Something went wrong at trying to load the dataset!!!")

        return retbool, datasetName


    ####################################################################################################################
    ####################################################################################################################



    @staticmethod
    def getOSPathes(operatingSystem=0):
        if operatingSystem==0:
            # my windows PC
            # pathDatabase = "D:" + os.sep + "med_data" + os.sep + "MRPhysics" + os.sep + "newProtocol"
            pathDatabase = 'C:' + os.sep + 'Users' + os.sep + 'hansw' + os.sep + 'Videos'\
                           + os.sep + 'artefacts' + os.sep + "MRPhysics" + os.sep + 'newProtocol'

            pathOutputPatching = "D:" + os.sep + "med_data" + os.sep + "MRPhysics" + os.sep + "DeepLearningArt_Output" + \
                os.sep + "Datasets"

            markingsPath = "D:" + os.sep + "med_data" + os.sep + "MRPhysics" + os.sep + "Markings"

            learningOutputPath = "D:" + os.sep + "med_data" + os.sep + "MRPhysics" + os.sep + "DeepLearningArt_Output" + \
                                      os.sep + "Output_Learning"

            pathOutputPatchingGAN = "D:" + os.sep + "med_data" + os.sep + "MRPhysics" + os.sep + "DeepLearningArt_GAN"

        elif operatingSystem==1:
            pathDatabase = "/med_data/ImageSimilarity/Databases/MRPhysics/newProtocol"
            pathOutputPatching = "/no_backup/d1237/DeepLearningArt_Output/Datasets"
            markingsPath = "/no_backup/d1237/Markings/"
            learningOutputPath = "/no_backup/d1237/DeepLearningArt_Output/Output_Learning"
            pathOutputPatchingGAN = "/no_backup/d1237/DeepLearningArt_GAN/"

        return pathDatabase, pathOutputPatching, markingsPath, learningOutputPath, pathOutputPatchingGAN
