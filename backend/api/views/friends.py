"""
api.views.friends
API endpoints for managing friendships:
- Send and respond to friend requests
- List accepted and pending friendships
- Remove friendships or cancel requests

Notes:
Responses are JSON-only (@renderer_classes([JSONRenderer])) and all
endpoints require authentication. Provides validation for duplicates,
authorization checks, and consistent status codes
"""

# Framework-generated: 0%
# Human-written: 60%
# AI-generated: 40% 

from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db import models
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.throttling import UserRateThrottle

class FriendRequestThrottle(UserRateThrottle):
    scope = 'friend_request'

from api.models.friends_models import Friend

User = get_user_model()

# Send a friend request 
@api_view(['POST'])
@renderer_classes([JSONRenderer])
@permission_classes([IsAuthenticated])
@throttle_classes([FriendRequestThrottle])
def send_friend_request(request, user_id):
    if str(request.user.id) == str(user_id): # Prevent users from friending themselves
        return Response({'detail': "Cannot send request to yourself"}, status=status.HTTP_400_BAD_REQUEST)

    to_user = get_object_or_404(User, pk=user_id)

    # check for existing accepted friendship (either direction)
    if Friend.objects.filter(sender=request.user, receiver=to_user, status='accepted').exists() or \
       Friend.objects.filter(sender=to_user, receiver=request.user, status='accepted').exists():
        return Response({'detail': "Friend request already exists or already friends"}, status=status.HTTP_400_BAD_REQUEST)

    # If there's already a pending request from the current user -> duplicate
    if Friend.objects.filter(sender=request.user, receiver=to_user, status='pending').exists():
        return Response({'detail': "Friend request already exists"}, status=status.HTTP_400_BAD_REQUEST)

    # If the target user already sent a pending request to the current user,
    # accept that request and return the accepted record (auto-match)
    reciprocal = Friend.objects.filter(sender=to_user, receiver=request.user, status='pending').first()
    if reciprocal:
        reciprocal.status = 'accepted'
        reciprocal.save()
        return Response({'id': str(reciprocal.pk), 'sender': str(reciprocal.sender.pk), 'receiver': str(reciprocal.receiver.pk), 'status': reciprocal.status}, status=status.HTTP_200_OK)

    # Create the pending friend request
    fr = Friend.objects.create(sender=request.user, receiver=to_user, status='pending')
    return Response({'id': str(fr.pk), 'sender': str(fr.sender.pk), 'receiver': str(fr.receiver.pk), 'status': fr.status},
                    status=status.HTTP_201_CREATED)

# Respond to a friend request
@api_view(['POST'])
@renderer_classes([JSONRenderer])
@permission_classes([IsAuthenticated])
def respond_to_friend_request(request, request_id):
    action = request.data.get('action')
    if action not in ('accept', 'reject'):
        return Response({'detail': "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

    fr = get_object_or_404(Friend, pk=request_id)

    # only receiver can respond
    if fr.receiver != request.user:
        return Response({'detail': "Not authorized"}, status=status.HTTP_403_FORBIDDEN)

    fr.status = 'accepted' if action == 'accept' else 'rejected'
    fr.save()
    return Response({'id': str(fr.pk), 'status': fr.status}, status=status.HTTP_200_OK)

# List accepted friends and pending requests for the authenticated user
# Returns three lists: friends (accepted), pending_sent, pending_received
@api_view(['GET'])
@renderer_classes([JSONRenderer])
@permission_classes([IsAuthenticated])
def list_friends(request):
    user = request.user

    # gather accepted friends where user is sender or receiver
    friends_qs = Friend.objects.filter(status='accepted').filter(
        models.Q(sender=user) | models.Q(receiver=user)
    )
    friends = []
    for f in friends_qs:
        # Figure out which user is "the other friend" in the relationship
        other = f.receiver if f.sender == user else f.sender
        # Provide minimal public fields (id and username) per API contract
        friends.append({'id': str(other.pk), 'username': getattr(other, 'username', '')})

    # pending sent and pending received lists
    pending_sent_qs = Friend.objects.filter(sender=user, status='pending')
    pending_received_qs = Friend.objects.filter(receiver=user, status='pending')

    # Normalize pending lists to minimal public shape (id and username)
    # Provide both the user's id (so frontend can map to user lists) and the
    # Friend record id (request_id) so the frontend can cancel by Friend.pk.
    outgoing_requests = [
        {
            'id': str(p.receiver.pk),
            'username': getattr(p.receiver, 'username', ''),
            'request_id': str(p.pk),
        }
        for p in pending_sent_qs
    ]
    incoming_requests = [
        {
            'id': str(p.sender.pk),
            'username': getattr(p.sender, 'username', ''),
            'request_id': str(p.pk),
        }
        for p in pending_received_qs
    ]

    # Return the shape defined in api.md while keeping old keys for compatibility
    response_payload = {
        'current_user_id': str(user.pk),
        'friends': friends,
        'incoming_requests': incoming_requests,
        'outgoing_requests': outgoing_requests,
    }

    return Response(response_payload, status=status.HTTP_200_OK)


# Remove a friend or cancel a friend request
@api_view(['DELETE'])
@renderer_classes([JSONRenderer])
@permission_classes([IsAuthenticated])
def remove_friend(request, request_id):
    """Delete a friendship or cancel a pending request

    endpoint is tolerant - `request_id` may be either the Friend record primary
    key (pk) or the other user's id. In the latter case we remove any Friend
    records that exist between the authenticated user and that other user
    """
    user = request.user
    # 1) Try to interpret request_id as a Friend.pk first
    fr = Friend.objects.filter(pk=request_id).first()
    if fr:
        if fr.sender != user and fr.receiver != user:
            return Response({'detail': "Not authorized"}, status=status.HTTP_403_FORBIDDEN)
        fr.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # 2) If not a Friend.pk, try treating friend_id as the other user's id
    try:
        other = get_object_or_404(User, pk=request_id)
    except Exception:
        # If we can't find a user by that id, return 404 to keep behaviour similar
        return Response({'detail': "Not found"}, status=status.HTTP_404_NOT_FOUND)

    # Find any Friend records between the authenticated user and the other user
    candidates = Friend.objects.filter(
        (models.Q(sender=user) & models.Q(receiver=other)) |
        (models.Q(sender=other) & models.Q(receiver=user))
    )

    if not candidates.exists():
        return Response({'detail': "Not found"}, status=status.HTTP_404_NOT_FOUND)

    # Ensure the authenticated user is a participant (should always be true here)
    # and delete all matching records to be defensive against duplicates
    deleted_count = 0
    for c in candidates:
        if c.sender == user or c.receiver == user:
            c.delete()
            deleted_count += 1

    if deleted_count == 0:
        return Response({'detail': "Not authorized"}, status=status.HTTP_403_FORBIDDEN)

    return Response(status=status.HTTP_204_NO_CONTENT)
