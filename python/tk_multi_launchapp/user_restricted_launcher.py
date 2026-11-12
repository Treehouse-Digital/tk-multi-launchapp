"""Implements "restrictions" settings by extending SingleConfigLauncher.

Restricted to these users (of these groups) that will have access an app.
Specify either name (str) or entity ID (int) into the "Users" and/or "Groups" lists e.g.

.. code-block:: yaml

    # <tk-config-default2>/env/includes/settings/tk-multi-launchapp.yml
    settings.tk-multi-launchapp.3de:
      location: "@apps.tk-multi-launchapp.location"
      menu_name: 3de
      restrictions:
        Users: ["John Doe", "Jane Smith", 123, 456]
        Groups: ["3D Team", 789]

"""

from collections.abc import Generator
from typing import Any

from .single_config_launcher import SingleConfigLauncher


class UserRestrictedLauncher(SingleConfigLauncher):
    """Extended to add ability to restrict software registered to specific users."""

    def register_launch_commands(self) -> None:
        """Extend to only register if user isn't restricted."""
        if self.check_restrictions(*self.found_restrictions()):
            super().register_launch_commands()
        else:
            self._tk_app.logger.warning("User restricted from %r", self._app_menu_name)

    def check_restrictions(
        self,
        user_restrictions: set[str | int],
        group_restrictions: set[str | int],
    ) -> bool:
        """Check restrictions given against current context's user.

        Returns whether the current user is allowed to register the app.

        Any of those restrictions given can be an empty set, which means no restrictions
        on that type. Values exactly matched and are assumed to be either entity IDs or
        names (the user belongs to).
        """
        valid = True

        if user_restrictions or group_restrictions:
            valid = False
            user_entity = self._tk_app.context.user
            if user_restrictions:
                valid_user_values: set[str | int] = {
                    user_entity["id"],
                    user_entity["name"],
                }
                valid = bool(valid_user_values & user_restrictions)

            if group_restrictions and not valid:
                valid_group_values: set[str | int] = set()
                groups = self._tk_app.shotgun.find(
                    "Group", [("users", "is", user_entity)], fields=["code"]
                )  # "is" in multi_entity behaves like 'contains'
                for group in groups:
                    valid_group_values |= {group["id"], group["code"]}
                valid = bool(valid_group_values & group_restrictions)

        return valid

    def _iter_checked_restrictions(
        self,
        key_name: str,
        values: list,
    ) -> Generator[str | int, None, None]:
        """Generate entity IDs/names after type checking the restriction values given.

        Internal use. The ``key_name`` denotes whether the restriction is from the
        "Users" or "Groups" key of the "restrictions" setting.
        """

        def msg(expected: str, element: str, obj: Any) -> str:
            return (
                f"Expected {expected} for restrictions[{element}], but got "
                f"{type(obj).__name__}: {obj!r}"
            )

        if not isinstance(values, list):
            raise TypeError(msg("list", repr(key_name), values))
        for index, value in enumerate(values):
            if not isinstance(value, (str, int)):
                raise TypeError(msg("str or int", f"{key_name!r}][{index}", value))
            yield value

    def found_restrictions(self) -> tuple[set[str | int], set[str | int]]:
        """Users and groups restrictions parsed from settings.

        Any of those can be an empty set.
        """
        restrictions = self._tk_app.get_setting("restrictions", {})

        user_restrictions: set[str | int] = set()
        if users := restrictions.get("Users"):
            user_restrictions = set(self._iter_checked_restrictions("Users", users))

        group_restrictions: set[str | int] = set()
        if groups := restrictions.get("Groups"):
            group_restrictions = set(self._iter_checked_restrictions("Groups", groups))

        return user_restrictions, group_restrictions
