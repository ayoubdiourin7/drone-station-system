import torch.nn as nn
#import torch.nn.functional as F
import torch.nn.init as init
import torch
import math

imageSize = 64

class AttrProxy(object):
    """Translates index lookups into attribute lookups."""
    def __init__(self, module, prefix):
        self.module = module
        self.prefix = prefix

    def __getitem__(self, i):
        return getattr(self.module, self.prefix + str(i))


class NetE(nn.Module):
    def __init__(self, nef):
        super(NetE, self).__init__()
        # state size: (nc) x 64 x 64
        self.conv1 = nn.Conv2d(3, nef, (4, 4), (2, 2), (1, 1), bias=False)
        self.conv1_bn = nn.BatchNorm2d(nef)
        self.conv1_relu = nn.LeakyReLU(0.2, inplace=False)
        # state size: (nef) x 32 x 32
        self.conv2 = nn.Conv2d(nef, nef*2, (4, 4), (2, 2), (1, 1), bias=False)
        self.conv2_bn = nn.BatchNorm2d(nef*2)
        self.conv2_relu = nn.LeakyReLU(0.2, inplace=False)
        # state size: (nef*2) x 16 x 16
        self.conv3 = nn.Conv2d(nef*2, nef*4, (4, 4), (2, 2), (1, 1), bias=False)
        self.conv3_bn = nn.BatchNorm2d(nef*4)
        self.conv3_relu = nn.LeakyReLU(0.2, inplace=False)
        # state size: (nef*4) x 8 x 8
        self.conv4 = nn.Conv2d(nef*4, nef*8, (4, 4), (2, 2), (1, 1), bias=False)
        self.conv4_bn = nn.BatchNorm2d(nef*8)
        self.conv4_relu = nn.LeakyReLU(0.2, inplace=False)
        # state size: (nef*8) x 4 x 4

        # channel-wise fully connected layer
        self.channel_wise_layers = []
        fla = int(imageSize**2/256)
        for i in range(0, 512):
            self.add_module('channel_wise_layers_' + str(i), nn.Linear(fla, fla))

        self.channel_wise_layers = AttrProxy(self, 'channel_wise_layers_')

        # state size: (nef*8) x 4 x 4
        self.dconv1 = nn.ConvTranspose2d(nef*8, nef*4, (4, 4), (2, 2), (1, 1), bias=False)
        self.dconv1_bn = nn.BatchNorm2d(nef*4)
        self.dconv1_relu = nn.ReLU(inplace=True)
        # state size: (nef*4) x 8 x 8
        self.dconv2 = nn.ConvTranspose2d(nef*4, nef*2, (4, 4), (2, 2), (1, 1), bias=False)
        self.dconv2_bn = nn.BatchNorm2d(nef*2)
        self.dconv2_relu = nn.ReLU(inplace=True)
        # state size: (nef*2) x 16 x 16
        self.dconv3 = nn.ConvTranspose2d(nef*2, nef, (4, 4), (2, 2), (1, 1), bias=False)
        self.dconv3_bn = nn.BatchNorm2d(nef)
        self.dconv3_relu = nn.ReLU(inplace=True)
        # state size: (nef) x 32 x 32
        self.dconv4 = nn.ConvTranspose2d(nef, 3, (4, 4), (2, 2), (1, 1), bias=False)
        self.dconv4_tanh = nn.Tanh()
        # self.dconv1_bn = nn.BatchNorm2d(3)
        # state size: (nc) x 64 x 64

        self._initialize_weights()

    def forward(self, x):
        x = self.conv1_relu(self.conv1_bn(self.conv1(x)))
        x = self.conv2_relu(self.conv2_bn(self.conv2(x)))
        x = self.conv3_relu(self.conv3_bn(self.conv3(x)))
        x = self.conv4_relu(self.conv4_bn(self.conv4(x)))

        for i in range(0, 512):
            slice_cur = x[:,[i],:,:]
            slice_cur_size = slice_cur.size()
            slice_cur = slice_cur.view(slice_cur_size[0], slice_cur_size[2]*slice_cur_size[3])
            slice_cur = self.channel_wise_layers[i](slice_cur)
            x[:,[i],:,:] = slice_cur.view(slice_cur_size[0], slice_cur_size[1], slice_cur_size[2], slice_cur_size[3])

        x = self.dconv1_relu(self.dconv1_bn(self.dconv1(x)))
        x = self.dconv2_relu(self.dconv2_bn(self.dconv2(x)))
        x = self.dconv3_relu(self.dconv3_bn(self.dconv3(x)))
        x = self.dconv4_tanh(self.dconv4(x))
        return x

    def _initialize_weights(self):

        init.normal_(self.conv1_bn.weight,  1.0, 0.02)
        init.normal_(self.conv2_bn.weight,  1.0, 0.02)
        init.normal_(self.conv3_bn.weight,  1.0, 0.02)
        init.normal_(self.conv4_bn.weight,  1.0, 0.02)
        init.normal_(self.dconv1_bn.weight, 1.0, 0.02)
        init.normal_(self.dconv2_bn.weight, 1.0, 0.02)
        init.normal_(self.dconv3_bn.weight, 1.0, 0.02)

        init.constant_(self.conv1_bn.bias,    0.0)
        init.constant_(self.conv2_bn.bias,    0.0)
        init.constant_(self.conv3_bn.bias,    0.0)
        init.constant_(self.conv4_bn.bias,    0.0)
        init.constant_(self.dconv1_bn.bias,   0.0)
        init.constant_(self.dconv2_bn.bias,   0.0)
        init.constant_(self.dconv3_bn.bias,   0.0)

        init.normal_(self.conv1.weight,  0.0, 0.02)
        init.normal_(self.conv2.weight,  0.0, 0.02)
        init.normal_(self.conv3.weight,  0.0, 0.02)
        init.normal_(self.conv4.weight,  0.0, 0.02)
        init.normal_(self.dconv1.weight, 0.0, 0.02)
        init.normal_(self.dconv2.weight, 0.0, 0.02)
        init.normal_(self.dconv3.weight, 0.0, 0.02)
        init.normal_(self.dconv4.weight, 0.0, 0.02)