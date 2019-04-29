import numpy as np
import math
from scipy.spatial import distance
import cv2


class video_metrics:
    def __init__(self, metrics_list, skip_frames, hash_size):
        self.hash_size = hash_size
        self.skip_frames = skip_frames
        self.metrics_list = metrics_list
        
    def rescale_pair(self, img_A, img_B):
        # Limit the scale to the minimum of the dimensions
        width = min(img_A.shape[0], img_B.shape[0])
        height = min(img_A.shape[1], img_B.shape[1])

        resized_A = cv2.resize(img_A, (height, width))
        resized_B = cv2.resize(img_B, (height, width))

        return resized_A, resized_B

    def mse(self, img_A, img_B):
        return np.mean( (img_A - img_B) ** 2 )

    def psnr(self, img_A, img_B):
        # Function to compute the Peak to Signal Noise Ratio (PSNR)
        # of a pair of images. img_A is considered the original and img_B
        # is treated as the noisy signal
        
        # Compute the Mean Square Error (MSE) between original and copy
        mse = np.mean( (img_A - img_B) ** 2 )

        # Compute PSNR as per definition in Wikipedia: 
        # https://en.wikipedia.org/wiki/Peak_signal-to-noise_ratio
        if mse == 0:
            return 100
        PIXEL_MAX = 255.0
        return 20 * math.log10(PIXEL_MAX / math.sqrt(mse))
        
    def dhash(self, image):
        # Function to compute the perceptual hash of an image

        # Resize the input image, adding a single column (width) so we
        # can compute the horizontal gradient
        resized = np.resize(image, (self.hash_size + 1, self.hash_size))
        # compute the (relative) horizontal gradient between adjacent
        # column pixels
        diff = resized[:, 1:] > resized[:, :-1]

        # convert the difference image to a hash
        hash = sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])
        hash_array = [int(x) for x in str(hash)]
        # Return only the first 15 elements of the array
        return hash_array[:15]

    def evaluate_difference_instant(self, current_frame, next_frame, frame_pos):
        # Function to compute the instantaneous difference between a frame
        # and its subsequent

        # Compute the number of different pixels
        total_pixels = current_frame.shape[0] * current_frame.shape[1]
        difference = np.array(next_frame - current_frame)
        difference_ratio = np.count_nonzero(difference) / total_pixels
    
        return difference_ratio
    
    def evaluate_dct_instant(self, reference_frame, rendition_frame, frame_pos):
        # Function that computes the matchTemplate function included in OpenCV and outputs the 
        # Maximum value

        reference_frame_float = np.float32(reference_frame)/255.0  # float conversion/scale
        reference_dct = cv2.dct(reference_frame_float)           # the dct
        
        rendition_frame_float = np.float32(rendition_frame)/255.0  # float conversion/scale
        rendition_dct = cv2.dct(rendition_frame_float)           # the dct
        

        _, max_val, _, _ = cv2.minMaxLoc(reference_dct - rendition_dct)

        return max_val

    def evaluate_cross_correlation_instant(self, reference_frame, rendition_frame):
        # Function that computes the Discrete Cosine Trasnform function included in OpenCV and outputs the 
        # Maximum value

        
        # Apply template Matching
        res = cv2.matchTemplate(reference_frame,rendition_frame, cv2.TM_CCORR_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)

        return max_val

    def evaluate_difference_canny_instant(self, reference_frame, next_reference_frame,  rendition_frame, next_rendition_frame):
        # Function to compute the instantaneous difference between a frame
        # and its subsequent, applying a Canny filter

        # Grab the frame skip_frames ahead of the present rendition
        
        scale_width = next_rendition_frame.shape[0]
        scale_height = next_rendition_frame.shape[1]

        # Compute the number of different pixels
        total_pixels = scale_width * scale_height

        # Compute the Canny edges for the reference frame, its next frame and the next frame of the rendition
        lower = 100
        upper = 200

        current_reference_edges = cv2.Canny(reference_frame, lower, upper)
        next_reference_edges = cv2.Canny(next_reference_frame, lower, upper)
        next_rendition_edges = cv2.Canny(next_rendition_frame, lower, upper)
        
        # Compute the difference between reference frame and its next frame
        reference_difference = np.array(next_reference_edges - current_reference_edges, dtype='uint8')
        
        # Compute the difference between reference frame and its corresponding next frame in the rendition
        rendition_difference = np.array(next_rendition_edges - current_reference_edges, dtype='uint8')

    
        # Create a kernel for dilating the Canny filtered images
        kernel = np.ones((int(scale_width * 0.1), int(scale_height * 0.1)),'uint8')

        # Apply the kernel to dilate and highlight the differences
        reference_difference_dilation = cv2.dilate(reference_difference, kernel, iterations=1)
        rendition_difference_dilation = cv2.dilate(rendition_difference, kernel, iterations=1)

        # Compute the difference ratio between reference frame (of original asset) and its next frame
        if np.count_nonzero(reference_difference_dilation) == 0:
            reference_ratio = total_pixels
        else:
            reference_ratio = total_pixels / np.count_nonzero(reference_difference_dilation)
        
        # Compute the difference ratio between reference frame (of original asset) and its next frame
        # in the rendition
        if np.count_nonzero(rendition_difference_dilation) == 0:
            rendition_ratio = total_pixels
        else:
            rendition_ratio = total_pixels / np.count_nonzero(rendition_difference_dilation) 

        difference = abs(1 / reference_ratio - 1/ rendition_ratio)

        return difference
    
    def evaluate_psnr_instant(self, reference_frame,  next_rendition_frame):
        # Function to compute the instantaneous PSNR between a frame
        # and its subsequent within a rendition

        scaled_reference, scaled_rendition = self.rescale_pair(reference_frame, next_rendition_frame)
        difference_psnr = self.psnr(scaled_reference, scaled_rendition)
        return difference_psnr

    def evaluate_mse_instant(self, reference_frame, next_rendition_frame):
        # Function to compute the instantaneous difference between a frame
        # and its subsequent

        scaled_reference, scaled_rendition = self.rescale_pair(reference_frame, next_rendition_frame)
        difference_mse = self.mse(scaled_reference, scaled_rendition)
        return difference_mse

    def histogram_distance(self, reference_frame, rendition_frame, bins=None, eps=1e-10):
        # compute a 3D histogram in the RGB colorspace,
        # then normalize the histogram so that images
        # with the same content, but either scaled larger
        # or smaller will have (roughly) the same histogram

        if bins is None:
            bins = [8, 8, 8]

        hist_a = cv2.calcHist([reference_frame], [0, 1, 2],
                              None, bins, [0, 256, 0, 256, 0, 256])
        hist_a = cv2.normalize(hist_a, hist_a)
        hist_b = cv2.calcHist([rendition_frame], [0, 1, 2],
                              None, bins, [0, 256, 0, 256, 0, 256])
        hist_b = cv2.normalize(hist_b, hist_b)

        # return out 3D histogram as a flattened array
        hist_a = hist_a.flatten()
        hist_b = hist_b.flatten()

        # Return the chi squared distance of the histograms
        d = 0.5 * np.sum([((a - b) ** 2) / (a + b + eps) for (a, b) in zip(hist_a, hist_b)])
        return d

    def compute_metrics(self, frame_pos, rendition_frame, next_rendition_frame, reference_frame, next_reference_frame):
        rendition_metrics = {}
        
        # Some metrics only need the luminance channel
        reference_frame_gray = cv2.cvtColor(reference_frame, cv2.COLOR_BGR2HSV)[:,:,2]
        next_reference_frame_gray = cv2.cvtColor(next_reference_frame, cv2.COLOR_BGR2HSV)[:,:,2]
        rendition_frame_gray = cv2.cvtColor(rendition_frame, cv2.COLOR_BGR2HSV)[:,:,2]
        next_rendition_frame_gray = cv2.cvtColor(next_rendition_frame, cv2.COLOR_BGR2HSV)[:,:,2]
        

        for metric in self.metrics_list:
            
            if metric == 'temporal_histogram_distance':
                rendition_metrics[metric] = self.histogram_distance(reference_frame, rendition_frame)

            if metric == 'temporal_difference':
                # Compute the temporal inter frame difference                
                rendition_metrics[metric] = self.evaluate_difference_instant(rendition_frame_gray, next_rendition_frame_gray,frame_pos)
            
            if metric == 'temporal_psnr':
                # Compute the temporal inter frame psnr                
                rendition_metrics[metric] = self.evaluate_psnr_instant(reference_frame_gray, next_rendition_frame_gray)
            
            if metric == 'temporal_mse':
                # Compute the temporal inter frame psnr                
                rendition_metrics[metric] = self.evaluate_mse_instant(reference_frame_gray, next_reference_frame_gray)

            if metric == 'temporal_canny':
                # Compute the temporal inter frame difference of the canny version of the frame
                rendition_metrics[metric] = self.evaluate_difference_canny_instant(reference_frame_gray, 
                                                                                    next_reference_frame_gray,
                                                                                    rendition_frame_gray, 
                                                                                    next_rendition_frame_gray)

            if metric == 'temporal_cross_correlation':
                rendition_metrics[metric] = self.evaluate_cross_correlation_instant(reference_frame_gray, 
                                                                                    rendition_frame_gray)

            if metric == 'temporal_dct':
                rendition_metrics[metric] = self.evaluate_dct_instant(reference_frame_gray, 
                                                                      rendition_frame_gray,
                                                                      frame_pos)

            # Compute the hash of the target frame
            rendition_hash = self.dhash(rendition_frame)
            # Extract the dhash for the reference frame            
            reference_hash = self.dhash(reference_frame)
            
            # Compute different distances with the hash
            if metric == 'hash_euclidean':
                rendition_metrics['hash_euclidean'] = distance.euclidean(reference_hash, rendition_hash)
            if metric == 'hash_hamming':
                rendition_metrics['hash_hamming'] = distance.hamming(reference_hash, rendition_hash)
            if metric == 'hash_cosine':
                rendition_metrics['hash_cosine'] = distance.cosine(reference_hash, rendition_hash)

        return rendition_metrics