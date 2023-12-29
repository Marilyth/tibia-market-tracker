import json
from utils.json_helper import object_to_json, json_to_object

class TestJsonHelper:
    def test_object_to_json_with_dict(self):
        # Arrange
        obj = {"name": "John", "age": 30, "city": "New York"}

        # Act
        result = object_to_json(obj)

        # Assert
        assert result is not None

    def test_object_to_json_with_list(self):
        # Arrange
        obj = ["apple", "banana", "cherry"]

        # Act
        result = object_to_json(obj)

        # Assert
        assert result is not None

    def test_object_to_json_with_string(self):
        # Arrange
        obj = "Hello, World!"

        # Act
        result = object_to_json(obj)

        # Assert
        assert result is not None

    def test_object_to_json_with_number(self):
        # Arrange
        obj = 12345

        # Act
        result = object_to_json(obj)

        # Assert
        assert result is not None

    def test_object_to_json_with_bool(self):
        # Arrange
        obj = True

        # Act
        result = object_to_json(obj)

        # Assert
        assert result is not None
    
    def test_object_to_json_with_class(self):
        # Arrange
        class Person:
            def __init__(self, name, age, children=None):
                self.name = name
                self.age = age
                self.children = children

        obj = Person("John", 36, [Person("John", 36), Person("John", 36), Person("John", 36)])

        # Act
        result = object_to_json(obj)
        reverse = json_to_object(result)

        # Assert
        assert result is not None
        assert reverse is not None
        assert reverse.name == obj.name
        assert reverse.age == obj.age
        assert reverse.children