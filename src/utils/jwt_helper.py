import jwt
from datetime import datetime, timedelta


class JWTHelper:
    def __init__(self, secret: str, algorithm: str = "HS256"):
        """Initializes the JWTHelper.

        Args:
            secret (str): The secret to use for the JWT.
        """
        self.secret = secret
        self.algorithm = algorithm

    def create_token(self, username: str, days: int = 90) -> str:
        """Creates a token for the given username.

        Args:
            username (str): The username to create a token for.

        Returns:
            str: The token.
        """
        payload = {
            "sub": username,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(days=days)
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def verify_token(self, token: str, verify_expired: bool = True):
        """Verifies the given token.

        Args:
            token (str): The token to verify.
            verify_expired (bool, optional): Whether to verify if the token has expired. Defaults to True.

        Returns:
            str: The username of the token.
        """
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm], options={"verify_exp": verify_expired})
            return payload.get("sub"), "Success"
        except jwt.ExpiredSignatureError:
            return None, "Token has expired."
        except Exception as e:
            print(f"Error while decoding token: {e}")
            return None, "Invalid token."
