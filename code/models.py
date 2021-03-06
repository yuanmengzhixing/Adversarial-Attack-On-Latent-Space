import torch
from torch import nn
import torch.nn.functional as F
from torch.autograd import Variable
from torch.nn.utils import clip_grad_norm
import numpy as np

# from functions import onehot

import os
from os.path import join

class VAE(nn.Module):

	def __init__(self, nz, imSize, fSize=2, sig=1):  #sig is the std of the prior
		super(VAE, self).__init__()
		#define layers here

		self.fSize = fSize
		self.nz = nz
		self.imSize = imSize
		self.sig = sig

		inSize = imSize / ( 2 ** 4)
		self.inSize = inSize

		self.enc1 = nn.Conv2d(3, fSize, 5, stride=2, padding=2)
		self.enc2 = nn.Conv2d(fSize, fSize * 2, 5, stride=2, padding=2)
		self.enc3 = nn.Conv2d(fSize * 2, fSize * 4, 5, stride=2, padding=2)
		self.enc4 = nn.Conv2d(fSize * 4, fSize * 8, 5, stride=2, padding=2)

		self.encLogVar = nn.Linear((fSize * 8) * inSize * inSize, nz)
		self.encMu = nn.Linear((fSize * 8) * inSize * inSize, nz)

		self.dec1 = nn.Linear(nz, (fSize * 8) * inSize * inSize)
		self.dec2 = nn.ConvTranspose2d(fSize * 8, fSize * 4, 3, stride=2, padding=1, output_padding=1)
		self.dec3 = nn.ConvTranspose2d(fSize * 4, fSize * 2, 3, stride=2, padding=1, output_padding=1)
		self.dec4 = nn.ConvTranspose2d(fSize * 2, fSize, 3, stride=2, padding=1, output_padding=1)
		self.dec5 = nn.ConvTranspose2d(fSize, 3, 3, stride=2, padding=1, output_padding=1)

	
		self.useCUDA = torch.cuda.is_available()

	def encode(self, x):
		#define the encoder here return mu(x) and sigma(x)
		x = F.relu(self.enc1(x))
		x = F.relu(self.enc2(x))
		x = F.relu(self.enc3(x))
		x = F.relu(self.enc4(x))
		x = x.view(x.size(0), -1)
		mu = self.encMu(x)  #no relu - mean may be zero
		log_var = self.encLogVar(x) #no relu - log_var may be negative
		
		return mu, log_var

	def sample_z(self, noSamples, sig=1):
		z =  sig * torch.randn(noSamples, self.nz)
		if self.useCUDA:
			return Variable(z.cuda())
		else:
			return Variable(z)

	def re_param(self, mu, log_var):
		#do the re-parameterising here
		sigma = torch.exp(log_var/2)  #sigma = exp(log_var/2) #torch.exp(log_var/2)
		if self.useCUDA:
			eps = Variable(torch.randn(sigma.size(0), self.nz).cuda())
		else: eps = Variable(torch.randn(sigma.size(0), self.nz))
		
		return mu + self.sig * sigma * eps  #eps.mul(simga)._add(mu)


	def decode(self, z):
		#define the decoder here
		z = F.relu(self.dec1(z))
		z = z.view(z.size(0), -1, self.inSize, self.inSize)
		z = F.relu(self.dec2(z))
		z = F.relu(self.dec3(z))
		z = F.relu(self.dec4(z))
		z = F.sigmoid(self.dec5(z))

		return z

	def forward(self, x):
		# the outputs needed for training
		mu, log_var = self.encode(x)
		z = self.re_param(mu, log_var)
		reconstruction = self.decode(z)

		return reconstruction, mu, log_var

	def loss(self, rec_x, x, mu, logVar):
		#Total loss is BCE(x, rec_x) + KL
		BCE = F.binary_cross_entropy(rec_x, x, size_average=False)  #not averaged over mini-batch if size_average=FALSE and is averaged if =True 
		#(might be able to use nn.NLLLoss2d())
		KL = 0.5 * torch.sum(mu ** 2 + torch.exp(logVar) - 1. - logVar) #0.5 * sum(1 + log(var) - mu^2 - var)
		return BCE / (x.size(2) ** 2),  KL / mu.size(1)

	def save_params(self, exDir):
		print 'saving params...'
		torch.save(self.state_dict(), join(exDir, 'vae_params'))


	def load_params(self, exDir):
		print 'loading params...'
		self.load_state_dict(torch.load(join(exDir, 'vae_params')))

class DISCRIMINATOR(nn.Module):

	def __init__(self, imSize, fSize=2, numLabels=1):
		super(DISCRIMINATOR, self).__init__()
		#define layers here

		self.fSize = fSize
		self.imSize = imSize

		inSize = imSize / ( 2 ** 4)
		self.numLabels = numLabels

		self.dis1 = nn.Conv2d(3, fSize, 5, stride=2, padding=2)
		self.dis2 = nn.Conv2d(fSize, fSize * 2, 5, stride=2, padding=2)
		self.dis3 = nn.Conv2d(fSize * 2, fSize * 4, 5, stride=2, padding=2)
		self.dis4 = nn.Conv2d(fSize * 4, fSize * 8, 5, stride=2, padding=2)
		self.dis5 = nn.Linear((fSize * 8) * inSize * inSize, numLabels)
	
		self.useCUDA = torch.cuda.is_available()

	def discriminate(self, x):
		x = F.relu(self.dis1(x))
		x = F.relu(self.dis2(x))
		x = F.relu(self.dis3(x))
		x = F.relu(self.dis4(x))
		x = x.view(x.size(0), -1)
		if self.numLabels == 1:
			x = F.sigmoid(self.dis5(x))
		else:
			x = F.softmax(self.dis5(x))
		
		return x

	def forward(self, x):
		# the outputs needed for training
		return self.discriminate(x)


	def save_params(self, exDir):
		print 'saving params...'
		torch.save(self.state_dict(), join(exDir,'class_dis_params'))


	def load_params(self, exDir):
		print 'loading params...'
		self.load_state_dict(torch.load(join(exDir,'class_dis_params')))














