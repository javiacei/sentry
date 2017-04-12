from __future__ import absolute_import

from django.db.models import Q
from operator import or_
from rest_framework.response import Response
from six.moves import reduce

from sentry.api.bases.organization import OrganizationEndpoint
from sentry.api.serializers import serialize
from sentry.api.serializers.models.group import StreamGroupSerializer
from sentry.models import (
    EventUser, Group, GroupTagValue
)


class OrganizationUserIssuesEndpoint(OrganizationEndpoint):
    def get(self, request, organization, user_id):
        limit = request.GET.get('limit', 100)

        euser = EventUser.objects.get(
            project__organization=organization,
            id=user_id,
        )

        other_eusers = euser.find_similar_users(request.user)
        event_users = [euser] + list(other_eusers)

        if event_users:
            tag_filters = [
                Q(value=eu.tag_value, project_id=eu.project_id)
                for eu in event_users
            ]
            tags = GroupTagValue.objects.filter(
                reduce(or_, tag_filters),
                key='sentry:user',
            )
        else:
            tags = GroupTagValue.objects.none()

        group_ids = tags.values_list('group_id', flat=True)

        groups = Group.objects.filter(
            id__in=group_ids,
        ).order_by('-last_seen')[:limit]

        context = serialize(
            list(groups), request.user, StreamGroupSerializer(
                stats_period=None
            )
        )

        return Response(context)