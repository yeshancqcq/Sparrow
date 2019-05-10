import h from 'react-hyperscript'
import {AppNavbar, NavButton} from 'app/shared/navbar'
import {SampleMap} from './map'
import {Frame} from './frame'

HomePage = ->
  h 'div', [
    h AppNavbar, {fullTitle: true}, [
      h NavButton, {to: '/admin'}, "Admin"
      h NavButton, {to: '/api-explorer/v1'}, "API Explorer"
    ]
    h Frame, {id: "landingText"}, "Landing page text goes here."
    h Frame, {id: "landingGraphic"}, (
      h SampleMap
    )
  ]

export {HomePage}
