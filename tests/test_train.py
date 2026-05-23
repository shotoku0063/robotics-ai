import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from train import parse_args, train  # noqa: E402


def test_parse_args_defaults():
    args = parse_args([])
    assert args.data == "data/processed"
    assert args.epochs == 100
    assert args.batch_size == 32
    assert args.lr == 1e-3


def test_parse_args_custom_epochs():
    args = parse_args(["--epochs", "50"])
    assert args.epochs == 50


def test_parse_args_custom_batch_size():
    args = parse_args(["--batch-size", "16"])
    assert args.batch_size == 16


def test_train_creates_output_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = os.path.join(tmpdir, "models", "run1")
        args = parse_args(["--output", output_dir])
        train(args)
        assert os.path.isdir(output_dir)
