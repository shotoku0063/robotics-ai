"""Model training script."""
import argparse
import torch
from pathlib import Path


def parse_args(args=None):
    parser = argparse.ArgumentParser(description='Train robotics AI model')
    parser.add_argument('--data', type=str, default='data/processed', help='Dataset path')
    parser.add_argument('--epochs', type=int, default=100)
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--lr', type=float, default=1e-3)
    parser.add_argument('--output', type=str, default='models/', help='Model save path')
    return parser.parse_args(args)


def train(args):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'Training on: {device}')

    # TODO: Replace with your dataset and model
    # dataset = YourDataset(args.data)
    # loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)
    # model = YourModel().to(device)

    Path(args.output).mkdir(parents=True, exist_ok=True)
    print('Training complete.')


if __name__ == '__main__':
    args = parse_args()
    train(args)
