"""Shared primitives for cassiopeia domain models."""

from typing import Annotated

from pydantic import AwareDatetime, Field

type NonEmptyString = Annotated[str, Field(min_length=1)]
type Slug = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
type AwareTimestamp = AwareDatetime
type EntityId = NonEmptyString
type ExternalId = NonEmptyString
