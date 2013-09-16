from flask import Blueprint, jsonify, current_app, abort
from critiquebrainz.db import db, Publication, Rate
from critiquebrainz.exceptions import *
from critiquebrainz.oauth import oauth
from critiquebrainz.parser import Parser

bp = Blueprint('publication', __name__)

@bp.route('/<uuid:publication_id>', endpoint='entity', methods=['GET'])
def publication_entity_handler(publication_id):
    publication = Publication.query.get_or_404(str(publication_id))
    if publication.is_archived is True:
        raise NotFound
    include = Parser.list('uri', 'inc', Publication.allowed_includes, optional=True) or []
    return jsonify(publication=publication.to_dict(include))

@bp.route('/<uuid:publication_id>', endpoint='delete', methods=['DELETE'])
@oauth.require_auth('publication')
def publication_delete_handler(publication_id, user):
    publication = Publication.query.get_or_404(str(publication_id))
    if publication.is_archived is True:
        raise NotFound
    if publication.user_id != user.id:
        raise AccessDenied
    publication.delete()
    return jsonify(message='Request processed successfully')

@bp.route('/<uuid:publication_id>', endpoint='modify', methods=['POST'])
@oauth.require_auth('publication')
def publication_modify_handler(publication_id, user):
    def fetch_params():
        text = Parser.string('json', 'text', min=25, max=2500)
        return text
    publication = Publication.query.get_or_404(str(publication_id))
    if publication.is_archived is True:
        raise NotFound
    if publication.user_id != user.id:
        raise AccessDenied
    text = fetch_params()
    publication.update(text=text)
    return jsonify(message='Request processed successfully',
                   publication=dict(id=publication.id))

@bp.route('/', endpoint='list', methods=['GET'])
def publication_list_handler():
    def fetch_params():
        release_group = Parser.uuid('uri', 'release_group', optional=True)
        user_id = Parser.uuid('uri', 'user_id', optional=True)
        sort = Parser.string('uri', 'sort', valid_values=['rating', 'created'], optional=True) or 'rating'
        limit = Parser.int('uri', 'limit', min=1, max=50, optional=True) or 50
        offset = Parser.int('uri', 'offset', optional=True) or 0
        include = Parser.list('uri', 'inc', Publication.allowed_includes, optional=True) or []
        return release_group, user_id, sort, limit, offset, include
    release_group, user_id, sort, limit, offset, include = fetch_params()
    publications, count = Publication.list(release_group, user_id, sort, limit, offset)
    return jsonify(limit=limit, offset=offset, count=count,
                   publications=[p.to_dict(include) for p in publications])

@bp.route('/', endpoint='create', methods=['POST'])
@oauth.require_auth('publication')
def publication_post_handler(user):
    def fetch_params():
        release_group = Parser.uuid('json', 'release_group')
        text = Parser.string('json', 'text', min=25, max=2500)
        if Publication.query.filter_by(user=user, release_group=release_group).count():
            raise InvalidRequest(desc='You have already published a review for this album')
        return release_group, text
    if user.is_publication_limit_exceeded:
        raise LimitExceeded('You have exceeded your limit of publications per day.')
    release_group, text = fetch_params()
    publication = Publication.create(user=user, text=text, release_group=release_group)
    return jsonify(message='Request processed successfully',
                   id=publication.id)

@bp.route('/<uuid:publication_id>/rate', methods=['GET'])
@oauth.require_auth('rate')
def publication_rate_entity_handler(publication_id, user):
    publication = Publication.query.get_or_404(str(publication_id))
    rate = Rate.query.filter_by(user=user, publication=publication).first()
    if not rate:
        raise NotFound
    else:
        return jsonify(rate=rate.to_dict())

@bp.route('/<uuid:publication_id>/rate', methods=['PUT'])
@oauth.require_auth('rate')
def publication_rate_put_handler(publication_id, user):
    def fetch_params():
        placet = Parser.bool('json', 'placet')
        return placet
    publication = Publication.query.get_or_404(str(publication_id))
    if publication.is_archived is True:
        raise NotFound
    placet = fetch_params()
    if publication.user_id == user.id:
        raise InvalidRequest(desc='You cannot rate your own publication.')
    if user.is_rate_limit_exceeded is True and user.has_rated(publication) is False:
        raise LimitExceeded('You have exceeded your limit of rates per day.')
    if placet is True and user.user_type not in publication.publication_class.upvote:
        raise InvalidRequest(desc='You are not allowed to upvote this publication.')
    if placet is False and user.user_type not in publication.publication_class.downvote:
        raise InvalidRequest(desc='You are not allowed to downvote this publication.')
    # overwrites an existing rate, if needed
    rate = Rate.create(user, publication, placet)
    return jsonify(message='Request processed successfully')

@bp.route('/<uuid:publication_id>/rate', methods=['DELETE'])
@oauth.require_auth('rate')
def publication_rate_delete_handler(publication_id, user):
    publication = Publication.query.get_or_404(str(publication_id))
    if publication.is_archived is True:
        raise NotFound
    rate = Rate.query.filter_by(user=user, publication=publication).first()
    if not rate:
        raise InvalidRequest(desc='Publication is not rated yet.')
    rate.delete()
    return jsonify(message='Request processed successfully')