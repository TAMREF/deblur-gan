import os
import datetime
import click
import numpy as np
from PIL import Image

from utils import load_images
from losses import adversarial_loss, generator_loss, wasserstein_loss, perceptual_loss, perceptual_loss_100
from model import generator_model, discriminator_model, generator_containing_discriminator, generator_containing_discriminator_multiple_outputs

from keras.optimizers import Adam

BASE_DIR = 'weights/'

def save_all_weights(d, g, epoch_number):
    now = datetime.datetime.now()
    save_dir = os.path.join(BASE_DIR, '{}{}'.format(now.month, now.day))
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    g.save_weights(os.path.join(save_dir, 'generator_{}.h5'.format(epoch_number)), True)
    d.save_weights(os.path.join(save_dir, 'discriminator_{}.h5'.format(epoch_number)), True)


def train_multiple_outputs(n_images, batch_size, epoch_num, critic_updates=5):
    data = load_images('./images/train', n_images)
    y_train, x_train = data['B'], data['A']

    g = generator_model()
    d = discriminator_model()
    d_on_g = generator_containing_discriminator_multiple_outputs(g, d)

    g_opt = Adam(lr=1E-4, beta_1=0.9, beta_2=0.999, epsilon=1e-08)
    d_opt = Adam(lr=1E-4, beta_1=0.9, beta_2=0.999, epsilon=1e-08)
    d_on_g_opt = Adam(lr=1E-4, beta_1=0.9, beta_2=0.999, epsilon=1e-08)

    d.trainable = True
    d.compile(optimizer=d_opt, loss=wasserstein_loss)
    d.trainable = False
    loss = [perceptual_loss, wasserstein_loss]
    loss_weights = [100, 1]
    d_on_g.compile(optimizer=d_on_g_opt, loss=loss, loss_weights=loss_weights)
    d.trainable = True

    first = True
    output_true_batch, output_false_batch = np.ones((batch_size, 1)), np.zeros((batch_size, 1))

    for epoch in range(epoch_num):
        print('epoch: {}/{}'.format(epoch, epoch_num))
        print('batches: {}'.format(x_train.shape[0] / batch_size))

        permutated_indexes = np.random.permutation(x_train.shape[0])

        for index in range(int(x_train.shape[0] / batch_size)):
            batch_indexes = permutated_indexes[index*batch_size:(index+1)*batch_size]
            image_blur_batch = x_train[batch_indexes]
            image_full_batch = y_train[batch_indexes]

            generated_images = g.predict(x=image_blur_batch, batch_size=batch_size)

            d_losses = []
            for _ in range(critic_updates):
                d_loss_real = d.train_on_batch(image_full_batch, output_true_batch)
                d_loss_fake = d.train_on_batch(generated_images, output_false_batch)
                d_loss = 0.5 * np.add(d_loss_fake, d_loss_real)
                d_losses.append(d_loss)
            print('batch {} d_loss : {}'.format(index+1, np.mean(d_losses)))

            d.trainable = False

            d_on_g_loss = d_on_g.train_on_batch(image_blur_batch, [image_full_batch, output_true_batch])
            print('batch {} d_on_g_loss : {}'.format(index+1, d_on_g_loss))

            d.trainable = True

        save_all_weights(d, g, epoch)

@click.command()
@click.option('--n_images', default=16, help='Number of images to load for training')
@click.option('--batch_size', default=16, help='Size of batch')
@click.option('--epoch_num', default=4, help='Number of epochs for training')
@click.option('--critic_updates', default=5, help='Number of discriminator training')
def train_command(n_images, batch_size, epoch_num, critic_updates):
    return train_multiple_outputs(n_images, batch_size, epoch_num, critic_updates)


if __name__ == '__main__':
    train_command()