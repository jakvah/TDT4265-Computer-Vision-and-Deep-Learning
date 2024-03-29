import numpy as np
import utils
import typing
np.random.seed(1)


def pre_process_images(X: np.ndarray):
    """
    Args:
        X: images of shape [batch size, 784] in the range (0, 255)
    Returns:
        X: images of shape [batch size, 785] normalized as described in task2a
    """
    assert X.shape[1] == 784,\
        f"X.shape[1]: {X.shape[1]}, should be 784"
    # Computing mean and std from training set
    new_X = np.zeros((X.shape[0], X.shape[1]+1))
    X_train, _, _, _ = utils.load_full_mnist()
    mean = np.mean(X_train)
    std = np.sqrt(np.cov(X_train.flatten()))
    # Normalizing
    new_X[:, :-1] = (X-mean)/std
    new_X[:, -1] = 1.0  # Bias Trick
    return new_X


def cross_entropy_loss(targets: np.ndarray, outputs: np.ndarray):
    """
    Args:
        targets: labels/targets of each image of shape: [batch size, num_classes]
        outputs: outputs of model of shape: [batch size, num_classes]
    Returns:
        Cross entropy error (float)
    """
    assert targets.shape == outputs.shape,\
        f"Targets shape: {targets.shape}, outputs: {outputs.shape}"
    cross_entropy = -np.sum(targets*np.log(outputs), axis=1)
    return np.mean(cross_entropy)


class SoftmaxModel:

    def __init__(self,
                 # Number of neurons per layer
                 neurons_per_layer: typing.List[int],
                 use_improved_sigmoid: bool,  # Task 3a hyperparameter
                 use_improved_weight_init: bool  # Task 3c hyperparameter
                 ):
        # Always reset random seed before weight init to get comparable results.
        np.random.seed(1)
        # Define number of input nodes
        self.I = 785
        self.use_improved_sigmoid = use_improved_sigmoid

        if self.use_improved_sigmoid:
            self.sigmoid = lambda X: 1.7159*np.tanh(2/3 * X)
            self.sigmoid_der = lambda X: 1.7159*2 / \
                (3*np.cosh(2*X / 3)**2)
        else:
            self.sigmoid = lambda X: 1 / (1 + np.exp(-X))
            self.sigmoid_der = lambda X: self.sigmoid(
                X) * (1 - self.sigmoid(X))

        # Define number of output nodes
        # neurons_per_layer = [64, 10] indicates that we will have two layers:
        # A hidden layer with 64 neurons and a output layer with 10 neurons.
        self.neurons_per_layer = neurons_per_layer
        self.layers = len(self.neurons_per_layer)
        self.hidden_layer_ouput = []
        self.zs = []

        # Initialize the weights
        self.ws = []
        prev = self.I
        for size in self.neurons_per_layer:
            w_shape = (prev, size)
            print("Initializing weight to shape:", w_shape)
            if use_improved_weight_init:
                w = np.random.normal(0, 1/np.sqrt(prev), (w_shape))
            else:
                w = np.random.uniform(-1, 1, (w_shape))
            self.ws.append(w)
            prev = size
        self.grads = [None for i in range(len(self.ws))]

    def forward(self, X: np.ndarray) -> np.ndarray:
        """
        Args:
            X: images of shape [batch size, 785]
        Returns:
            y: output of model with shape [batch size, num_outputs]
        """
        # Reset the lists
        self.hidden_layer_ouput = []
        self.zs = []

        logits = X  # Initialize z
        self.hidden_layer_ouput.append(logits)
        # Minus 1 is not include the last layer with softmax
        for i in range(self.layers - 1):
            z = logits @ self.ws[i]
            logits = self.sigmoid(z)

            # Store z and f(z)
            self.zs.append(z)
            self.hidden_layer_ouput.append(logits)
        z = logits @ self.ws[-1]

        return np.exp(z) / (np.sum(np.exp(z), axis=1)[:, None])

    def backward(self, X: np.ndarray, outputs: np.ndarray,
                 targets: np.ndarray) -> None:
        """
        Computes the gradient and saves it to the variable self.grad

        Args:
            X: images of shape [batch size, 785]
            outputs: outputs of model of shape: [batch size, num_outputs]
            targets: labels/targets of each image of shape: [batch size, num_classes]
        """
        assert targets.shape == outputs.shape,\
            f"Output shape: {outputs.shape}, targets: {targets.shape}"
        # A list of gradients.
        # For example, self.grads[0] will be the gradient for the first hidden layer
        self.grads = []
        batch_size = X.shape[0]

        delta_k = -(targets-outputs)  # BP1
        first_grad = self.hidden_layer_ouput[-1].T @ delta_k  # BP4
        self.grads.insert(0, first_grad/batch_size)

        delta = delta_k
        # Delta has shape batch_size, nodes_for_ layer_l
        for i in range(1, self.layers):
            sig_der = self.sigmoid_der(self.zs[-i])
            delta = (delta @ self.ws[-i].T) * sig_der  # BP2
            self.grads.insert(
                0, (self.hidden_layer_ouput[-i-1].T @ delta)/batch_size)  # BP4

        for grad, w in zip(self.grads, self.ws):
            assert grad.shape == w.shape,\
                f"Expected the same shape. Grad shape: {grad.shape}, w: {w.shape}."

    def zero_grad(self) -> None:
        self.grads = [None for i in range(len(self.ws))]


def one_hot_encode(Y: np.ndarray, num_classes: int):
    """
    Args:
        Y: shape [Num examples, 1]
        num_classes: Number of classes to use for one-hot encoding
    Returns:
        Y: shape [Num examples, num classes]
    """
    one_hot = np.zeros((Y.shape[0], num_classes), dtype=int)
    one_hot[np.array(range(len(Y))), Y.flatten()] = 1
    return one_hot


def gradient_approximation_test(
        model: SoftmaxModel, X: np.ndarray, Y: np.ndarray):
    """
        Numerical approximation for gradients. Should not be edited.
        Details about this test is given in the appendix in the assignment.
    """
    epsilon = 1e-3
    for layer_idx, w in enumerate(model.ws):
        for i in range(w.shape[0]):
            for j in range(w.shape[1]):
                orig = model.ws[layer_idx][i, j].copy()
                model.ws[layer_idx][i, j] = orig + epsilon
                logits = model.forward(X)
                cost1 = cross_entropy_loss(Y, logits)
                model.ws[layer_idx][i, j] = orig - epsilon
                logits = model.forward(X)
                cost2 = cross_entropy_loss(Y, logits)
                gradient_approximation = (cost1 - cost2) / (2 * epsilon)
                model.ws[layer_idx][i, j] = orig
                # Actual gradient
                logits = model.forward(X)
                model.backward(X, logits, Y)
                difference = gradient_approximation - \
                    model.grads[layer_idx][i, j]
                assert abs(difference) <= epsilon**2,\
                    f"Calculated gradient is incorrect. " \
                    f"Layer IDX = {layer_idx}, i={i}, j={j}.\n" \
                    f"Approximation: {gradient_approximation}, actual gradient: {model.grads[layer_idx][i, j]}\n" \
                    f"If this test fails there could be errors in your cross entropy loss function, " \
                    f"forward function or backward function"


if __name__ == "__main__":
    # Simple test on one-hot encoding
    Y = np.zeros((1, 1), dtype=int)
    Y[0, 0] = 3
    Y = one_hot_encode(Y, 10)
    assert Y[0, 3] == 1 and Y.sum() == 1, \
        f"Expected the vector to be [0,0,0,1,0,0,0,0,0,0], but got {Y}"

    X_train, Y_train, *_ = utils.load_full_mnist()
    X_train = pre_process_images(X_train)
    Y_train = one_hot_encode(Y_train, 10)
    assert X_train.shape[1] == 785,\
        f"Expected X_train to have 785 elements per image. Shape was: {X_train.shape}"

    neurons_per_layer = [64, 10]
    use_improved_sigmoid = False
    use_improved_weight_init = False
    model = SoftmaxModel(
        neurons_per_layer, use_improved_sigmoid, use_improved_weight_init)

    # Gradient approximation check for 100 images
    X_train = X_train[:100]
    Y_train = Y_train[:100]
    for layer_idx, w in enumerate(model.ws):
        model.ws[layer_idx] = np.random.uniform(-1, 1, size=w.shape)

    gradient_approximation_test(model, X_train, Y_train)
