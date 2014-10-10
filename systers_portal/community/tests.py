from django.test import TestCase
from django.contrib.auth.models import Group, User
from django.db.models.signals import post_save
from guardian.shortcuts import get_perms

from community.models import Community
from community.permissions import groups_templates, group_permissions
from community.signals import manage_community_groups
from community.utils import create_groups, assign_permissions, remove_groups
from users.models import SystersUser


class CommunityTestCase(TestCase):
    def setUp(self):
        post_save.disconnect(manage_community_groups, sender=Community,
                             dispatch_uid="create_groups")

    def test_create_groups(self):
        name = "Foo"
        groups = create_groups(name)
        expected_group_names = []
        for key, group_name in groups_templates.items():
            expected_group_names.append(group_name.format(name))
        group_names = []
        for group in groups:
            group_names.append(group.name)
        self.assertListEqual(expected_group_names, group_names)

        community_groups = Group.objects.filter(name__startswith=name)
        self.assertListEqual(list(community_groups), groups)

    def test_assign_permissions(self):
        User.objects.create(username='foo', password='foobar')
        systers_user = SystersUser.objects.get()
        community = Community.objects.create(name="Foo", slug="foo", order=1,
                                             community_admin=systers_user)
        name = community.name
        groups = create_groups(name)
        assign_permissions(community, groups)
        for key, value in group_permissions.items():
            group = Group.objects.get(name=groups_templates[key].format(name))
            group_perms = [p.codename for p in
                           list(group.permissions.all())]
            group_perms += get_perms(group, community)
            self.assertItemsEqual(group_perms, value)

    def test_original_values(self):
        User.objects.create(username='foo', password='foobar')
        systers_user = SystersUser.objects.get()
        name = "Foo"
        community = Community.objects.create(name=name, slug="foo", order=1,
                                             community_admin=systers_user)
        self.assertEqual(community.original_name, name)
        self.assertEqual(community.community_admin, systers_user)
        community.name = "Bar"
        user = User.objects.create(username="bar", password="barfoo")
        systers_user2 = SystersUser.objects.get(user=user)
        community.community_admin = systers_user2
        community.save()
        self.assertEqual(community.original_name, name)
        self.assertEqual(community.original_community_admin, systers_user)

    def test_remove_groups(self):
        name = "Foo"
        create_groups(name)
        remove_groups(name)
        community_groups = Group.objects.filter(name__startswith=name)
        self.assertEqual(list(community_groups), [])
