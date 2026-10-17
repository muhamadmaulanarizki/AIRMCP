@extends('layouts.landing')

@section('title', $brand['name'] . ' — ' . $brand['tagline'])
@section('description', $brand['description'])

@section('content')
    @include('landing.sections.hero')
    @include('landing.sections.menu')
    @include('landing.sections.about')
    @include('landing.sections.location')
    @include('landing.sections.contact')
@endsection
