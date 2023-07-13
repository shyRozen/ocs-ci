from ocs_ci.ocs import constants
from ocs_ci.ocs.ocp import OCP
from ocs_ci.ocs.ui.page_objects.data_foundation_tabs_common import (
    DataFoundationDefaultTab,
    CreateResourceForm,
    DataFoundationTabBar,
)


class NameSpaceStoreTab(DataFoundationDefaultTab, CreateResourceForm):
    def __init__(self):
        DataFoundationTabBar.__init__(self)
        CreateResourceForm.__init__(self)
        self.rules = {
            constants.UI_INPUT_RULES_NAMESPACE_STORE[
                "rule1"
            ]: self._check_max_length_backing_store_rule,
            constants.UI_INPUT_RULES_NAMESPACE_STORE[
                "rule2"
            ]: self._check_start_end_char_rule,
            constants.UI_INPUT_RULES_NAMESPACE_STORE[
                "rule3"
            ]: self._check_only_lower_case_numbers_periods_hyphens_rule,
            constants.UI_INPUT_RULES_NAMESPACE_STORE[
                "rule4"
            ]: self._check_namespace_store_not_used_before_rule,
        }
        self.name_input_loc = self.validation_loc["namespacestore_name"]

    def _check_namespace_store_not_used_before_rule(self, rule_exp) -> bool:
        """
        Checks whether the namespace store name allowed to use again.

        This function executes an OpenShift command to retrieve the names of all existing namespace stores
        in all namespaces.
        It then checks whether the name of the existed namespace store would be allowed to use.

        Args:
            rule_exp (str): the rule requested to be checked. rule_exp text should match the text from validation popup

        Returns:
            bool: True if the namespace name has not been used before, False otherwise.
        """
        existing_namespace_store_names = str(
            OCP().exec_oc_cmd(
                "get namespacestore --all-namespaces -o custom-columns=':metadata.name'"
            )
        )
        return self._check_resource_name_not_exists_rule(
            existing_namespace_store_names, rule_exp
        )
