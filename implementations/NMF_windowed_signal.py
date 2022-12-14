import numpy as np
import re
import math
import pandas as pd
import librosa 
import music21
window_size = 1
## Signal parametes
fs = 22050      # sample frequency

## STFT parameters
N = 1024        # frame size
q = 0.5         # overlap factor for the window. some people use 0.9

## NINOS2 parameters
lambda_ = 1     # compression ratio
gamma_ = 1      # fraction of frequency bins used, keeps everything. 0.1 would mean keeping the lowest 10 percent.

## peak picking parameters 
alpha_ = 1      # before maximum, 
beta_ = 1       # after maximum
a = 3           # before average, 
b = 2           # after average
delta_ = 0.5     # offset from neighboorhood average, how far from the average you want.

# NORMALIZE NINOS

def ninos_func(X, lambda_, gamma_):

    ## Calculate number of frequency bins
    J = int(gamma_*(X.shape[0]-1)) 

    ## Sort lower J log values of X
    Y = np.zeros((J, X.shape[1]))
    Y_temp = np.sort(np.log10(lambda_*np.abs(X)+1),axis=0)
    Y = Y_temp[0:J,:]

    ## Inverse sparsity
    ninos = np.zeros(Y.shape[1])
    for i in range(Y.shape[1]):
        #ninos[i] = (np.linalg.norm(Y[:,i])**2)/(np.power(J,1/4)*sum(abs(Y[:,i])**4)**(1./4))  
        ninos[i] = np.linalg.norm(Y[:,i])*((np.linalg.norm(Y[:,i])/sum(abs(Y[:,i])**4)**(1./4))-1)/(np.power(J,1/4)-1)

    return ninos 

def peak_pick(ninos, alpha_, beta_, a, b, delta_, N, q):
    
    ## Calculate combination width
    Theta_ = int(np.ceil(N/(np.rint((1-q)*N))))
    
    return librosa.util.peak_pick(ninos, alpha_,beta_,a,b,delta_,Theta_)


def add_to_note_info(cps,W,H,S,segment,sr, note_info,s,onset_times):
    # for every component
    temp_note_info = []
    for n in range(cps):
        # get the coresponding spectral profile
        spectral = W[:,n]
        # get the corresponding temporal profile
        temporal = H[n]

        # get the highest activation in the spectral profile
        note = np.argmax(spectral) * (sr/2)/S.shape[0]
        # get the highest activation in temporal profile
        onset = np.argmax(temporal)/S.shape[1]
        # add the info to the temporary array
        temp_note_info += [[onset,n,note]]

    # sort the array based on increasing onset time
    temp_note_info= sorted(temp_note_info)
    # sort the onsets from Wannes' code increasing onset time
    onset_times = sorted(onset_times)
    # use the info in temp array to index Wannes' onsets
    for info in temp_note_info:
        # error correct the onsets, use the estimated onset from H to index the onsets from
        # Wannes' code
        # adds onset, note
        note_info += [[(segment-window_size)+round(onset_times[info[1]],2),round(info[2])]]

    # calculate durations
    note_info = sorted(note_info)
    last_onset = 0

    # until last element, loop through note info
    for i in range(len(note_info)-1):
        # if i has already 3 elements, it means duration was calculated in the previous segment
        # continue to the next iteration
        if(len(note_info[i]) == 3):
            continue
        # next element - current element is the duration of the current note
        duration = note_info[i+1][0] - note_info[i][0] 
        # add it to the note_info
        note_info[i] += [round(duration,2)]
        # update the last onset
        last_onset = note_info[i][0]

    # check if the note  info aray has elements
    if len(note_info) != 0:
        # using the last onset handle the last element in the note info array
        if len(temp_note_info) == 1:
            note_info[-1] += [round(segment-note_info[-1][0],2)]
        else:
            note_info[-1] += [round(segment-last_onset,2)]

        # append the notes to the music stream
        # TODO: adding the duration and other attributes for the midi file
        for i in note_info:
            n = music21.note.Note(i[1]) 
            s.append(n)

    return note_info,s
        



def window(duration,x,sr,tempo):
    # variables to return when transcription is done
    note_info = []
    s = music21.stream.Stream()
    ##====================================== 
    ## take the next 2 second segment
    #curr_x = x 
    ## apply STFT
    #S = librosa.stft(curr_x,n_fft=N)


    ## Code from Wannes for onset detection
    #odf = ninos_func(S, lambda_, gamma_)
    #onsets = peak_pick(odf, alpha_, beta_, a, b, delta_, N, q)
    #onset_times = librosa.frames_to_time(onsets)

    ## estimate reduced rank R for NMF
    #cps = len(onset_times)
    ## if there are no onsets continue to the next iteration
    ## decompose spectrogram S to magnitude and phase
    #X, X_phase = librosa.magphase(S)
    ## use the Magnitude spectrum of S to do NMF, fit=True, components are estimated from X
    #W, H = librosa.decompose.decompose(X,n_components=cps, fit=True)
    ## using W and onset times, populate the note_info
    #note_info,s = add_to_note_info(cps,W,H,S,1,sr,note_info,s,onset_times)
    #====================================== 
    #take 2 second segments from the recording and apply NMF on them
    for i in range(window_size,round(duration)+1,window_size):
        # take the next 2 second segment
        curr_x = x[(i-window_size)*sr:sr*i] 
        # apply STFT
        # TODO: FIND OUT A GOOD N_FFT FOR STFT
        # n_fft = number of fft bins This parameter specifies the length of the Fast Fourier Transform (FFT) 
        # window that is used to analyze each frame of the audio signal
        # should be set to largest expected periodicity.
        S1 = librosa.stft(curr_x,n_fft=int(sr/8))



        # Code from Wannes for onset detection
        odf = ninos_func(S1, lambda_, gamma_)
        onsets = peak_pick(odf, alpha_, beta_, a, b, delta_, N, q)
        onset_times = librosa.frames_to_time(onsets)

        # estimate reduced rank R for NMF
        cps = len(onset_times)
        print(cps)
        # if there are no onsets continue to the next iteration
        if cps == 0:
            continue
        # decompose spectrogram S to magnitude and phase
        X, X_phase = librosa.magphase(S1)
        # use the Magnitude spectrum of S to do NMF, fit=True, components are estimated from X
        W, H = librosa.decompose.decompose(X,n_components=cps, fit=True)
        # using W and onset times, populate the note_info
        note_info,s = add_to_note_info(cps,W,H,S1,i,sr,note_info,s,onset_times)
    return note_info,s




if __name__=='__main__':
    path = "/Users/keremokyay/masters/SPAI/Project-sessions/data/drum_mic2.wav"
    test_path = "/Users/keremokyay/Documents/labeled_data_SPAI/part2.txt"
    f = open(test_path)
    labels = []
    for line in f:
        line = line.strip('\n')
        row = re.split(';', line)
        row = row[:-1]
        for i in range(3):
            if i == 2:
                row[i] = int(row[i])
            elif len(row[i]) >=7:
                row[i] = row[i][:-4]
                row[i] = round(float(row[i]),2)
        labels += [row]
    # load the file
    x,sr = librosa.load(path)
    
    # calculate duration to loop through
    duration = len(x) / sr

    # calculate tempo 
    tempo, beats = librosa.beat.beat_track(y=x,sr=sr)
    tempo=int(2*round(tempo/2))
    print(tempo)
    # create the music21 object for tempo
    mm = music21.tempo.MetronomeMark(referent='quarter', number=tempo)

    # start the transcription
    note_info,s = window(duration,x,sr,tempo)

    s.append(mm)
    onset_frames = librosa.onset.onset_detect(x, sr=sr, wait=1, pre_avg=1, post_avg=1, pre_max=1, post_max=1)
    onset_times = librosa.frames_to_time(onset_frames)
    print(note_info)


    # find the onsets that are in +- 0.1 
    correct_onsets = 0
    correct_onsets_within_02 = 0

    correct_notes = 0
    correct_notes_within_20 = 0

    correct_duration = 0
    correct_duration_within_01 = 0

    for label in labels:
        onset = label[0]
        duration = label[1] - label[0]
        note = label[2]

        for prediction in note_info:
            onset_pred = prediction[0]
            duration_pred = prediction[1] - prediction[0]
            note_pred = prediction[2]

            if round(onset_pred,1) == round(onset,1):
                correct_onsets += 1
            elif np.abs(onset - onset_pred) <= 0.2: 
                correct_onsets_within_02 +=1
            if note == note_pred:
                correct_notes += 1
            elif np.abs(note-note_pred) <=20:
                correct_notes_within_20 += 1
            if duration == duration_pred:
                correct_duration += 1
            elif np.abs(note-note_pred) <=0.1:
                correct_duration_within_01 += 1

    print("total number of predicted onsets:      ", len(note_info), "total number of ground truth onsets: ", len(labels))
    print("number of correct onsets predicted:    ", correct_onsets, " number of onsets within 0.2 seconds of the ground truth: ", correct_onsets_within_02)
    print("number of correct predicted notes:     ", correct_notes, " number of notes within 20 Hz of the ground truth: ", correct_notes_within_20 )
    print("number of correct predicted duraitons: ", correct_duration, " number of durations within 0.1 seconds of the ground truth: ", correct_duration_within_01 )


                
    
    #s.show()
    #s.write('midi', fp='midi_drum.mid')
