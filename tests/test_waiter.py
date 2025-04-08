from utils.waiter import wait_until


def test_WaitUntilTrue_PredicateReturnsTrue_ReturnsTrue():
    # Assign
    def func():
        return True

    # Act
    result = wait_until(func)

    # Assert
    assert result

def test_WaitUntilTrue_PredicateReturnsFalse_ReturnsFalse():
    # Assign
    def func():
        return False

    # Act
    result = wait_until(func, timeout=0.1)

    # Assert
    assert not result

def test_WaitUntilTrue_PredicateReturnsTrueAfterTimeout_ReturnsFalse():
    # Assign
    counter = 0

    def func():
        nonlocal counter
        counter += 1
        return counter > 20

    # Act
    result = wait_until(func, timeout=0.1, interval=0.01)

    # Assert
    assert not result

def test_WaitUntilTrue_PredicateReturnsTrueBeforeTimeout_ReturnsTrue():
    # Assign
    counter = 0

    def func():
        nonlocal counter
        counter += 1
        return counter > 5

    # Act
    result = wait_until(func, timeout=0.1, interval=0.01)

    # Assert
    assert result