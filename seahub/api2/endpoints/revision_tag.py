# Copyright (c) 2012-2016 Seafile Ltd.
import os

from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from django.utils.translation import ugettext as _

from seahub.api2.throttling import UserRateThrottle
from seahub.api2.authentication import TokenAuthentication
from seahub.api2.utils import api_error
from seahub.revision_tag import models

import seaserv
from seaserv import seafile_api


def check_parameter(func):
    """Check that the parameters are valid.Check user permission.If it's DELETE method,check that commit_id exists 
    """
    def _decorated(view, request, repo_id, *args, **kwargs):
        if not repo_id:
            return api_error(status.HTTP_400_BAD_REQUEST, _("Repo id can not be empty"))
   
        if request.method in ["POST", "DELETE"]:
            commit_id = kwargs.get("commit_id", "")
            if request.method == "POST":
                tag_name = request.POST.get("tag_name", "")
            if request.method == "DELETE":
                tag_name = kwargs.get("tag_name")
            if not tag_name or '/' in tag_name:
                error_msg = _("Tag name can not be empty")
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)
            if not commit_id:
                error_msg = _("Commit id can not be empty")
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)
            if request.method == "DELETE":
                if tag_name not in models.Tags.objects.get_all_tag_name():
                    error_msg = _("Tag name %s does not exists"%(tag_name, ))
                    return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        repo = seafile_api.get_repo(repo_id)
        if not repo:
            error_msg = _("Repo id %s does not exists" % repo_id)
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        if not seafile_api.check_permission(repo_id, request.user.username):
            error_msg = _('Permission denied.')
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        if request.method in ["POST", "DELETE"]:
            commit = seaserv.get_commit(repo.id, repo.revision, commit_id)
            if not commit:
                error_msg = _("Commit id %s does not exists" % commit_id)
                return api_error(status.HTTP_400_BAD_REQUEST, error_msg)
            kwargs = {}
            return func(view, request, 
                        repo_id, commit_id, 
                        tag_name, *args, **kwargs)
        return func(view, request, repo_id, *args, **kwargs)
    return _decorated

class RevisionTags(APIView):
    """Query/Add a specific RevisionTags.
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, )
    throttle_classes = (UserRateThrottle, )

    @check_parameter
    def get(self, request, repo_id):
        revision_tags = models.RevisionTags.objects.get_all_revision_tag_by_repo(repo_id)
        return Response({
                "tags":[revision_tag.to_dict() for revision_tag in revision_tags]
        })

    @check_parameter
    def post(self, request, repo_id, commit_id, tag_name):
        revision_tag, created = models.RevisionTags.objects.create_revision_tag(
            repo_id, 
            commit_id, 
            tag_name,
            request.user.username
        )
        if created:
            return Response({"success": True}, status=status.HTTP_201_CREATED)
        else:
            return Response({"success": True})

class RevisionTag(APIView):
    """Delete a specific RevisionTags.
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, )
    throttle_classes = (UserRateThrottle, )

    @check_parameter
    def delete(self, request, repo_id, commit_id, tag_name):
        if models.RevisionTags.objects.delete_revision_tag(
                repo_id, 
                commit_id,
                tag_name):
            return Response({"success": True})
        else:
            return Response({"success": True}, status=status.HTTP_202_ACCEPTED)
