import torch
import torch.nn as nn

# Model definition
class CNNLSTM(nn.Module):
    def __init__(self, input_channels, num_classes):
        super(CNNLSTM, self).__init__()
        self.cnn = nn.Sequential(
            nn.Conv2d(input_channels, 16, 3, padding=1),  # was 32
            nn.ReLU(),
            nn.MaxPool2d(2),  # 63x63

            nn.Conv2d(16, 32, 3, padding=1),  # was 64
            nn.ReLU(),
            nn.MaxPool2d(2),  # 31x31

            nn.Conv2d(32, 64, 3, padding=1),  # was 128
            nn.ReLU(),
            nn.MaxPool2d(2)  # 15x15
        )

        # Infer CNN output size
        with torch.no_grad():
            dummy_input = torch.zeros(1, input_channels, 127, 127)
            cnn_output_dim = self.cnn(dummy_input).view(1, -1).shape[1]

        self.lstm = nn.LSTM(input_size=cnn_output_dim,
                            hidden_size=64,  # reduced
                            batch_first=True,
                            bidirectional=False)  # saves 2x parameters

        self.classifier = nn.Sequential(
            nn.Linear(64, 32),  # was 128*2 → 64
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(32, num_classes)
        )

    def forward(self, x):
        B, T, C, H, W = x.shape
        x = x.view(B * T, C, H, W)
        x = self.cnn(x)
        x = x.view(B, T, -1)
        out, _ = self.lstm(x)
        return self.classifier(out[:, -1, :])
