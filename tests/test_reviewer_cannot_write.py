import inspect
import meg.review.reviewers as reviewers
def test_reviewer_has_no_promoter_or_config_writer_path():
 source=inspect.getsource(reviewers)
 assert "Promoter" not in source and "ConfigStore" not in source
